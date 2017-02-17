import os
import sys
import re
import csv
from urllib.parse import urlparse
from urllib.request import urlretrieve


class NychvsSasImport():
    '''
    Single purpose of class is to download and cleanup data from 2014 NYCHVS
    and fix some import errors along the way
    proc_file - SAS Import file
    attributes - fields to fix [you can change 'start' position, 'width' 'format']
                 'format' - only 'id' - implied decimal supported
    data_file_list = IGNORE
    '''
    def __init__(self, proc_file, attributes={}, data_file_list=[]):
        self._proc_file = proc_file
        self.__data_dict = {}
        self.__data_labels = {}
        self.__file_names = data_file_list
        self._attributes = attributes

    @property
    def proc_file(self):
        return self._proc_file

    @property
    def attributes(self):
        return self._attributes

    def fix_file_name(self, wrong_filename):
        cur_dir = os.getcwd()
        file_list = os.listdir()
        partial_match, ext = wrong_filename.split('.')
        corrected_file_name = [s for s in file_list if
                               partial_match in s]
        if len(corrected_file_name) > 1:
            corrected_file_name = [k for k in corrected_file_name if
                                   k.endswith('.txt') or k.endswith('.dat')]
        return corrected_file_name[0]

    def format_string(self, string, format_code):
        # Made up this format - id - impled decimal SAS COMMA9.5 codes
        if 'id' in format_code:
            digits = int(format_code.split('.')[1][0])
            val = float(string)
            exp = 10**digits
            return_str = str(val/exp)
        return return_str

    def read_to_data_dictionary(self):
        with open(self._proc_file) as proc_file:
            current_file = None
            current_block = sys.maxsize
            for num, line in enumerate(proc_file, 1):
                if 'infile' in line:
                    m = re.search(r".*\\(.*)\'.*", line)
                    if m is None:
                        continue
                    current_file = m.groups(0)[0]
                    current_file = self.fix_file_name(current_file)
                    self.__file_names.append(current_file)
                    current_block = sys.maxsize
                if 'do' in line:
                    current_block = num
                if '@' in line and num > current_block:
                    m = re.search(r".*@(\d+)\s*(\w+)\s*[a-zA-z\$]+(\d+)\..*",
                                  line)
                    if m is None:
                        print(line)
                        continue
                    start = int((m.groups(0)[0]))-1
                    label = (m.groups(0)[1])
                    end = start + int((m.groups(0)[2]))
                    conversion_format = None
                    # if label == 'uf39a': #SAS file wrongly coded
                    #   end = start + 1
                    if label in self._attributes.keys():
                        if 'start' in self._attributes[label]:
                            start = self._attributes[label]['start']
                        if 'width' in self._attributes[label]:
                            end = start + self._attributes[label]['width']
                        if 'format' in self._attributes[label]:
                            conversion_format = self._attributes[label]['format']
                    if current_file not in self.__data_dict:
                        self.__data_dict[current_file] = [[label,
                                                           slice(start,end),
                                                           conversion_format]]
                    else:
                        self.__data_dict[current_file].append([label,
                                                               slice(start,end),
                                                               conversion_format])
                if 'label' in line and num > current_block:
                    m = re.search(r".*label\s+(\w+)=\'(.*)\';", line)
                    if m is None:
                        continue
                    label = m.groups(0)[0]
                    desc = m.groups(0)[1]
                    if label not in self.__data_labels:
                        self.__data_labels[label] = desc
            for file in self.__data_dict.keys():
                print('Identified File {0} with {1} fields in SAS Script'.
                      format(file, len(self.__data_dict[file])))
            return None

    def to_csv(self):
        for file in self.__file_names:
            self.write_data_to_csv(file)

    def write_data_to_csv(self, data_file):
        out_file = data_file.split('.')[0] + '.csv'
        with open(out_file, 'w') as outfile:
            writer = csv.writer(outfile, delimiter=',', quotechar='"',
                                quoting=csv.QUOTE_MINIMAL)
            row = [field[0] for field in self.__data_dict[data_file]]
            writer.writerow(row)
            with open(data_file) as file:
                for num, line in enumerate(file, 1):
                    # row=[line[field[1]] for field in self.__data_dict[data_file]]
                    row = []
                    for field in self.__data_dict[data_file]:
                        label = field[0]
                        value = line[field[1]]
                        if label in self._attributes:
                            if 'format' in self._attributes[label]:
                                value = self.format_string(
                                              value,
                                              self._attributes[label]['format'])
                        row.append(value)
                    writer.writerow(row)
            print("Finished writing {0}...".format(out_file))
        return None


if __name__ == '__main__':
    urls = \
      ["https://www.census.gov/housing/nychvs/data/2014/uf_14_occ_web_b.txt",
        "https://www.census.gov/housing/nychvs/data/2014/uf_14_pers_web_b.txt",
        "https://www.census.gov/housing/nychvs/data/2014/uf_14_vac_web.dat",
        "https://www.census.gov/housing/nychvs/data/2014/sas_import_program.txt"
       ]

    for url in urls:
        file_name = os.path.split(urlparse(url).path)[-1]
        dl_path = os.path.join(os.path.curdir, file_name)
        urlretrieve(url, dl_path)

    sas = NychvsSasImport('./sas_import_program.txt',
                          {'uf39a': {'width': 1}, 'fw': {'format': '{:0.5id}'},
                           'chufw': {'format': '{:0.5id}'}})
    sas.read_to_data_dictionary()
    sas.to_csv()
