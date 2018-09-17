from perso_lib.ini_parse import IniParser
from perso_lib import utils

class Dgi:
    def __init__(self):
        self.dgi = ''
        self.tag_value_dict = dict()

    def add_tag_value(self,tag,value):
        if tag not in self.tag_value_dict.keys():
            self.tag_value_dict[tag] = value

    def modify_value(self,tag,value):
        if tag in self.tag_value_dict.keys():
            self.tag_value_dict[tag] = value

    def remove_tag(self,tag):
        if tag in self.tag_value_dict.keys():
            del self.tag_value_dict[tag]

    def get_value(self,tag):
        if tag in self.tag_value_dict.keys():
            return self.tag_value_dict[tag]
    
    def get_all_tags(self):
        return self.tag_value_dict
    
    def assemble_tlv(self,tag,data):
        '''拼接TLV格式，不考虑数据长度超过0xFF的情况'''
        data_len = len(data)
        if data_len >= 0x80:
            return tag + '81' + utils.get_strlen(data) + data
        else:
            return tag + utils.get_strlen(data) + data

#dgi only contains '_' and 'PSE','PPSE'
def _custom_sorted(dgi):
    number = 0
    if dgi.dgi == 'PSE':
        return 0x9FFFFF
    elif dgi.dgi == 'PPSE':
        return 0xAFFFFF
    elif '_' in dgi.dgi:
        value = dgi.dgi.replace('_','0')
        number = utils.hex_str_to_int(value)
    else:
        number = utils.hex_str_to_int(dgi.dgi)
    return number

class Cps:
    def __init__(self):
        self.dgi_list = []

    def add_dgi(self,dgi):
        '''添加DGI分组，若该DGI分组存在,则直接合并其中的tag'''
        for dgi_item in self.dgi_list:
            if dgi_item.dgi == dgi.dgi:
                tag_value_dict = dgi.get_all_tags()
                for tag,value in tag_value_dict.items():
                    dgi_item.add_tag_value(tag,value)
                break
        else:
            self.dgi_list.append(dgi)

    def remove_dgi(self,dgi):
        for item in self.dgi_list:
            if item.dgi == dgi:
                self.dgi_list.remove(item)
                return
    
    def get_dgi(self,dgi):
        for item in self.dgi_list:
            if dgi == item.dgi:
                return item
    
    def save(self,file_name,sort=_custom_sorted):
        open(file_name,'w+')    #make sure file is existed.
        ini = IniParser(file_name)
        self.dgi_list.sort(key=_custom_sorted)
        for item in self.dgi_list:
            ini.add_section(item.dgi)
            for key,value in item.tag_value_dict.items():
                ini.add_option(item.dgi,key,value)

    def get_account(self,tag='5A'):
        ret = ''
        for item in self.dgi_list:
            ret = item.get_value(tag)
            if ret is not None:
                if 'F' in ret:
                    return ret[4 : len(ret) - 1]
                else:
                    return ret[4 :]
        return ret

    def get_all_dgis(self):
        dgis = []
        for item in self.dgi_list:
            dgis.append(item.dgi)
        return dgis





if __name__ == '__main__':
    cps = Cps()
    dgi = Dgi()
    dgi.dgi = '0101'
    dgi.add_tag_value('9F1F','ABCD')
    dgi.add_tag_value('5F24','2018009')
    dgi.modify_value('9F1F','xxxx')
    dgi.remove_tag('5F24')
    cps.add_dgi(dgi)
    dgi = Dgi()
    dgi.dgi = '0201'
    dgi.add_tag_value('9F1F','YYYY')
    cps.add_dgi(dgi)
    cps.save('D:\\xxx.txt')
