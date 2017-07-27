from scipy.sparse import dok_matrix
import efficient_find_next_max
import pylab as pl
import data_point
import sys
import numpy as np

class Matrix():

    def __init__(self, dfr, parameters):

        self.parameters = parameters

        self.list_all_data_points = self.load_data_points_in_list(dfr)

        self.get_unique_mz_values()

        self.int_matrix = dok_matrix((len(self.unique_mz_list), len(self.mz_by_scan)), dtype=pl.float32)
#        self.to_mod_int_matrix = dok_matrix((len(self.unique_mz_list), len(self.mz_by_scan)), dtype=pl.float32)

        self.create_matrix()

        self.efficient_next_max = efficient_find_next_max.EfficientNextMax(self.list_all_data_points)

    def load_data_points_in_list(self, dfr):

        absolute_intensity_thresh = self.parameters['absolute_intensity_thresh']

        self.mz_by_scan = []
        self.inten_by_scan = []
        self.rt = []
        self.scan_numbers = []
        list_all_data_points = []

        self.count = 0

        mz, inten = dfr.get_next_scan_mzvals_intensities()

        while mz is not None:
            sys.stdout.write("\r" + str(self.count))
            sys.stdout.flush()
            self.mz_by_scan.append(mz)
            self.inten_by_scan.append(inten)
            self.rt.append(dfr.get_rt_from_scan_num(self.count))
            self.scan_numbers.append(dfr.get_act_scan_num(self.count))
            for i in range(len(mz)):
                if inten[i] < absolute_intensity_thresh:
                    continue
                cur_dp = data_point.DataPoint(self.count, i, mz[i], inten[i])
                list_all_data_points.append(cur_dp)

            mz, inten = dfr.get_next_scan_mzvals_intensities()

            self.count += 1

        return list_all_data_points

    def get_unique_mz_values(self):

        self.unique_mzs = {}
        self.unique_mz_list = []

        print "Building unique_mzs \n"
        print "..."

        for i in range(len(self.mz_by_scan)):
            for j in range(len(self.mz_by_scan[i])):
                cur_mz = self.mz_by_scan[i][j]
                cur_mz = int(cur_mz * self.parameters['mz_factor'])
                try:
                    self.unique_mzs[cur_mz]
                except KeyError:
                    self.unique_mzs[cur_mz] = True

        print "Done building unique_mzs \n"

        print ("len(unique_mzs): " + str(len(self.unique_mzs)))

        for i in self.unique_mzs:
            self.unique_mz_list.append(i)

        print "Full mz range of specified region:"
        print "     min(unique_mz_list): " + str(min(self.unique_mz_list) / 10000.0)
        print "     max(unique_mz_list): " + str(max(self.unique_mz_list) / 10000.0)
        print "     len(unique_mz_list): " + str(len(self.unique_mz_list))
        print "Full RT range of specified region:"
        print "     rt[0]: " + str(self.rt[0])
        print "     rt[-1]: " + str(self.rt[-1])
        print "     len(rt): " + str(len(self.rt))



    def create_matrix(self):

        self.list_all_data_points.sort(key=lambda x: x.intensity, reverse=True)
        self.rt = pl.array(self.rt) / 60.0
        self.unique_mz_list.sort()

        self.mz_to_index_map = {}

        count_2 = 0
        c = len(self.list_all_data_points)

        for i in range(len(self.unique_mz_list)):
            self.mz_to_index_map[self.unique_mz_list[i]] = i

        for i in self.list_all_data_points:
            if count_2 % (c / 10) == 0:
                print "%.1f percent" % (float(count_2) / float(c) * 100.0)

            cur_mz = i.mz
            cur_mz = int(cur_mz * self.parameters['mz_factor'])
            cur_scan_index = i.scan_index
            cur_intensity = i.intensity

            cur_mz_index = self.mz_to_index_map[cur_mz]
            i.mz_index = cur_mz_index

            self.int_matrix[cur_mz_index, cur_scan_index] = cur_intensity
#            self.to_mod_int_matrix[cur_mz_index, cur_scan_index] = cur_intensity

            count_2 += 1

    def find_max(self):

        return self.efficient_next_max.find_max()

    def index_to_mz(self, index):

        return self.unique_mz_list[index]

    def construct_EIC(self, int_mz_value, first_scan_boundary, second_scan_boundary, parameters):

        mz_int_tolerance = parameters['mz_factor'] * parameters['mz_tolerance']

        mz_tolerance_index_list = []

        first_int_mz_boundary = int_mz_value - mz_int_tolerance
        second_int_mz_boundary = int_mz_value + mz_int_tolerance

        for unique_mz in self.unique_mz_list:
            if unique_mz > first_int_mz_boundary and unique_mz < second_int_mz_boundary:
                mz_tolerance_index_list.append(self.mz_to_index_map[unique_mz])

        mz_start = max(0, min(mz_tolerance_index_list))
        mz_end = min(self.int_matrix.shape[0], max(mz_tolerance_index_list))

        first_scan_boundary = max(0, first_scan_boundary)
        second_scan_boundary = min(self.int_matrix.shape[1], second_scan_boundary)

        inten_array = self.int_matrix[mz_start:mz_end + 1, first_scan_boundary:second_scan_boundary + 1].toarray().max(axis=0)
        rt_array = []

        for scan in range(first_scan_boundary, second_scan_boundary):
            rt = self.rt[scan]
            rt_array.append(rt)

        return np.array(rt_array), inten_array

    def remove_cur_max(self, mz_index, scan_index, first_scan_boundary, second_scan_boundary):

        first_scan_boundary = max(0, first_scan_boundary)
        second_scan_boundary = min(self.int_matrix.shape[1], second_scan_boundary)

        self.int_matrix[mz_index, scan_index] = 0
        efficient_find_next_max.EfficientNextMax.done_with_rows_cols(self.efficient_next_max, mz_index, mz_index + 1, first_scan_boundary, second_scan_boundary + 1)