# 该仅对通用的规则进行转换，对于DP中特殊的处理
# 请在DP处理模块中进行处理
import importlib
import os
import shutil
import time
from enum import Enum
from xml.dom import Node
from perso_lib.cps import Cps,Dgi
from perso_lib import algorithm
from perso_lib import utils
from perso_lib.kms import Kms
from perso_lib.xml_parse import XmlParser,XmlMode
from perso_lib.word import Docx
from perso_lib.file_handle import FileHandle
from perso_lib.excel import ExcelMode,ExcelOp
from perso_lib import settings
from perso_lib.log import Log

Log.init()

alias_count = 0
def get_alias():
    global alias_count
    print('alias:' + str(alias_count))
    alias_count += 1
    return 'alias' + str(alias_count)


# 定义数据类型枚举,仅在MC 1156表中使用
class MediaType(Enum):
    FCI         = 0     #MC 专用
    SHARED      = 1     #MC 专用
    CONTACT     = 2
    CONTACTLESS = 3
    INTERNAL    = 4     #MC 专用
    MAGSTRIPE   = 5     #MC 专用

class AppType(Enum):
    '''
    除了UICS类型用来区分
    '''
    VISA_DEBIT  = 'VISA_DEBIT'  #VISA 借记
    VISA_CREDIT = 'VISA_CREDIT' #VISA 贷记
    MC_DEBIT    = 'MC_DEBIT'    #MC 借记
    MC_CREDIT   = 'MC_CREDIT'   #MC 贷记
    UICS_DEBIT  = 'UICS_DEBIT'  #UICS 借记
    UICS_CREDIT = 'UICS_CREDIT' #UICS 贷记
    JETCO       = 'JETCO'       #JETCO
    AMEX        = 'AMEX'        #AMEX
    JCB         = 'JCB'         #JCB
    PURE        = 'PURE'        #PURE

class SourceItem:
    '''
    该类描述了获取的元数据格式
    '''
    def __init__(self):
        self.name = ''      #tag的英文名称
        self.tag = ''       #tag标签
        self.len = ''       #tag长度
        self.value = ''     #tag值
        self.data_type = None   #标识数据值类型,fixed,file,kms
        self.media_type = None #tag介质类型
        self.used = False   #个人化时，是否被使用到

class TagInfo:
    '''
    tag 需要从文件中获取值的tag
    convert_to_ascii 是否需要转换为ASCII码
    value 一种描述取值方式的字符串,例如 "[10,20]001[12,33]"
    表示从emboss file中取位置10到20的字符串 + 固定字符串001 + 从emboss file取位置12到33的字符串
    '''
    def __init__(self):
        self.tag = ''               # tag标签
        self.convert_to_ascii = False   # 是否需要转ASCII
        self.convert_to_bcd = False  #是否需要转BCD
        self.replace_equal_by_D = False # 是否需要 将=变D
        self.trim_right_space = False   # 是否需要取掉值右边的空格
        self.value = '' # tag值
        self.source = None    # tag来源 contact或contactless
        self.live = '' # 针对tag9F10测试环境和正式环境,DKI值不同
        self.comment = ''   # tag描述

# 港澳地区专用的纯Jetco应用Excel表格
class JetcoForm:
    def __init__(self,ca_file,issuer_file,ic_pk_file,ic_private_file,excel_file):
        self.ca_file = ca_file
        self.issuer_file = issuer_file
        self.ic_pk_file = ic_pk_file
        self.ic_private_file = ic_private_file
        self.excel_file = excel_file
        self.ca_pk_len = 0
        self.excel = ExcelOp(excel_file)
        self.data_list = []

    def set_mdk(self,mdk_ac,mdk_mac,mdk_enc):
        self.mdk_ac = mdk_ac
        self.mdk_mac = mdk_mac
        self.mdk_enc = mdk_enc

    def read_data(self,title_list,card_no):
        self.read_excel_data(title_list,card_no)
        self.read_cert_data()
        app_key = self.gen_8000(self.mdk_ac,self.mdk_mac,self.mdk_enc)
        self.gen_9000(app_key)
        return self.data_list

    def gen_8000(self,mdk_ac,mdk_mac,mdk_enc):
        tag5A = ''
        tag5F34 = ''
        for item in self.data_list:
            if item.tag == '5A':
                tag5A = item.value
            if item.tag == '5F34':
                tag5F34 = item.value
        tag8000 = algorithm.gen_app_key(mdk_ac,mdk_mac,mdk_enc,tag5A,tag5F34)
        data_item = SourceItem()
        data_item.tag = '8000'
        data_item.value = tag8000
        data_item.media_type = 'contact'
        self.data_list.append(data_item)
        return tag8000

    def gen_9000(self,tag8000):
        tag9000 = algorithm.gen_app_key_kcv(tag8000)
        data_item = SourceItem()
        data_item.tag = '9000'
        data_item.value = tag9000
        data_item.media_type = 'contact'
        self.data_list.append(data_item)
        return tag9000

    def read_excel_data(self,title_list,card_no,sheet_name='Sheet1',start_row=4,start_col=1):
        if self.excel.open_worksheet(sheet_name):
            has_find = False
            for row in range(start_row,200):
                data = self.excel.read_cell_value(row,title_list[0][1])
                if data == card_no:
                        has_find = True
                        start_row = row
                        break
            if has_find:
                title_list = title_list[1:]
                for title in title_list:
                    data = self.excel.read_cell_value(start_row,title[1])
                    if data:
                        data = data.strip()
                        if data == 'Empty':
                            data = ''
                        if title[0] == '5A' and len(data) % 2 != 0:
                            data = data + 'F'
                        item = SourceItem()
                        item.media_type = 'contact'
                        item.tag = title[0]
                        item.value = data
                        self.data_list.append(item)
        return self.data_list
        
    def read_cert_data(self):
        tag_value_list = []
        tag_value_list += self._handle_ca_file()
        tag_value_list += self._handle_issuer_file()
        tag_value_list += self._handle_ic_private_file()
        tag_value_list += self._handle_ic_pk_file()
        for item in tag_value_list:
            data_item = SourceItem()
            data_item.media_type = 'contact'
            data_item.tag = item[0]
            data_item.value = item[1]
            self.data_list.append(data_item)

    
    def _handle_ic_private_file(self):
        fh = FileHandle(self.ic_private_file,'rb+')
        head = fh.read_binary(fh.current_offset, 33)
        data_list = []
        while not fh.EOF:
            flag = fh.read_binary(fh.current_offset,1)
            if flag != '02':
                print('read ic private file failed.')
                return
            data_len = fh.read_binary(fh.current_offset,1)
            if data_len == '81':
                data_len = fh.read_binary(fh.current_offset,1)
            data_len = utils.hex_str_to_int(data_len)
            data = fh.read_binary(fh.current_offset,data_len)
            if data[0:2] == '00': #凭经验，此处若为00，表示多余的一个字节
                data = data[2:]
            data_list.append(data)
        tag_values = []
        tag_values.append(('8201',data_list[7]))
        tag_values.append(('8202',data_list[6]))
        tag_values.append(('8203',data_list[5]))
        tag_values.append(('8204',data_list[4]))
        tag_values.append(('8205',data_list[3]))
        return tag_values

    def _handle_ic_pk_file(self):
        fh = FileHandle(self.ic_pk_file,'rb+')
        head = fh.read_binary(fh.current_offset, 1)
        pan = fh.read_binary(fh.current_offset, 10)  
        sn = fh.read_binary(fh.current_offset, 3)
        expirate_date = fh.read_binary(fh.current_offset, 2)
        icc_remainder_len = fh.read_short(fh.current_offset)
        icc_remainder = fh.read_binary(fh.current_offset,icc_remainder_len)
        exp_len = fh.read_short(fh.current_offset)
        exp = fh.read_binary(fh.current_offset,exp_len)
        icc_pk_len = fh.file_size - fh.current_offset
        icc_pk = fh.read_binary(fh.current_offset,icc_pk_len)
        tag_values = []
        tag_values.append(('9F46',icc_pk))
        tag_values.append(('9F47',exp))
        tag_values.append(('9F48',icc_remainder))
        Log.info("9F46:" + icc_pk)
        Log.info("9F47:" + exp)
        Log.info("9F48:" + icc_remainder)
        return tag_values

    def _handle_issuer_file(self):
        fh = FileHandle(self.issuer_file,'rb+')
        head = fh.read_binary(fh.current_offset, 1)
        service_ident = fh.read_binary(fh.current_offset,4)
        issuer_ident = fh.read_binary(fh.current_offset,4)
        sn = fh.read_binary(fh.current_offset,3)
        expirate_date = fh.read_binary(fh.current_offset, 2)
        issuer_remainder_len = fh.read_short(fh.current_offset)
        issuer_remainder = fh.read_binary(fh.current_offset,issuer_remainder_len)
        exp_len = fh.read_short(fh.current_offset)
        exp = fh.read_binary(fh.current_offset,exp_len)
        ca_pk_index = fh.read_binary(fh.current_offset,1)
        issuer_pk = fh.read_binary(fh.current_offset,self.ca_pk_len)
        other_len = fh.file_size - fh.current_offset
        other = fh.read_binary(fh.current_offset,other_len)
        tag_values = []
        tag_values.append(('90',issuer_pk))
        tag_values.append(('92',issuer_remainder))
        tag_values.append(('9F32',exp))
        Log.info("90:" + issuer_pk)
        Log.info("92:" + issuer_remainder)
        Log.info("9F32:" + exp)
        return tag_values       


    def _handle_ca_file(self):
        fh = FileHandle(self.ca_file,'rb+')
        head = fh.read_binary(fh.current_offset, 1)
        service_ident = fh.read_binary(fh.current_offset,4)
        self.ca_pk_len = fh.read_int(fh.current_offset)
        algo = fh.read_binary(fh.current_offset,1)
        exp_len = int(fh.read_binary(fh.current_offset,1))
        rid = fh.read_binary(fh.current_offset,5)
        ca_index = fh.read_binary(fh.current_offset,1)
        ca_pk_mod = fh.read_binary(fh.current_offset,self.ca_pk_len)
        exp = fh.read_binary(fh.current_offset,exp_len)
        tag_values = []
        # tag_values.append(('8F',ca_index))
        Log.info('ca_mod: ' + ca_pk_mod)
        Log.info('ca_exp: ' + exp)
        return tag_values

class GoldpacForm:
    '''
    获取金邦达专用的Excel表格中的数据
    '''
    def __init__(self,sheet_name):
        self.excel = ExcelOp(sheet_name) #sheet_name为Excel表格中的表名
        self.source_items = []  #存储Excel表中的数据项
        
    def get_data(self,tag,media_type,desc=None):
        for item in self.source_items:
            if item.media_type == media_type and item.tag == tag:
                item.used = True
                return item.value
        return None
    
    def _get_data(self,row,col,ignore_list=None):
        # 列名分别是:Data Category,Name,Tag,Length,recommended value,Issuer settings,data source,remarks
        source_item = SourceItem()
        source_item.name = self.excel.read_cell_value(row,col + 1)    #Name
        source_item.tag = self.excel.read_cell_value(row,col + 2)    #Tag
        #source_item.len = self.excel.read_cell_value(row,col + 3)     # 不使用Excel表中的长度定义，使用setting.py中的长度定义
        source_item.value = self.excel.read_cell_value(row,col + 5)   # Issuer settings
        source_item.data_type = self.excel.read_cell_value(row,col + 6) # Emboss File,Kms,Fixed

        if source_item.name:
            source_item.name = source_item.name.replace('\n',' ')

        # 忽略掉value为N.A或者为空的数据项
        if source_item.value and source_item.value != 'N.A':
            # 1. 清理tag列数据
            if source_item.tag:
                source_item.tag = str(source_item.tag).strip() #有些可能读表格时，默认是int类型，需要转str
                temp = source_item.tag.split('-')
                if len(temp) == 2 and temp[1].strip():
                    source_item.tag = temp[0].strip()
                    source_item.media_type = temp[1].strip().lower()
                else:
                    source_item.media_type = 'contact'

            # 2. 清理数据项的数据类型
            if source_item.data_type == 'Fixed':
                source_item.data_type = 'fixed'   #保持和模板xml中的type一致
            elif source_item.data_type == 'Emboss File':
                source_item.data_type = 'file'
            elif source_item.data_type == 'Kms':
                source_item.data_type = 'kms'
                source_item.value = 'kms'

            # 3. 清理value列数据,过滤掉空格和换行符,
            source_item.value = str(source_item.value)
            source_item.value = source_item.value.replace('\n','').replace(' ','')
            # Excel表中，可以不区分大小写和空格，这个统一转为小写形式
            if source_item.value.lower() == 'empty':
                source_item.value = 'empty' #如果为empty,也需要个人化此tag
            # elif not utils.is_hex_str(source_item.value) and  source_item.tag != '9F10': #此时认为是不合规的值
            #     Log.error('parse tag %s error: value is incorrect format',source_item.tag)
            #     source_item.value = None

        if source_item.value and source_item.tag:
            return source_item
        return None

    def read_data(self,sheet_name,start_row=5,start_col=2):
        Log.info('start read data...')
        self.source_items.clear() #读数据前，将旧数据清空
        if self.excel.open_worksheet(sheet_name):
            first_header = self.excel.read_cell_value(start_row,start_col)
            if str(first_header).strip() != 'Data Category':
                Log.error('can not found form start position,row:%scol:%s',start_row,start_col)
                return None
            start_row += 1 #默认标题行之后就是数据行
            for row in range(start_row,200):
                item = self._get_data(row,start_col)    #获取每行数据，组成一个SourceItem对象
                if item:
                    if item.value != 'N.A':
                        self.source_items.append(item)
                        Log.info("tag:{0:15s} |value:{1:40s}|desc:{2}".format(item.tag,item.value,item.name))
                    else:
                        Log.warn("tag:{0:15s} |value:{1:40s}|desc:{2}".format(item.tag,item.value,item.name))
        return self.source_items[:]


class McForm:
    def __init__(self,xml_name):
        self.source_items = []
        self.xml_handle = XmlParser(xml_name,XmlMode.READ)

    def read_data(self):
        worksheet_nodes = self.xml_handle.get_child_nodes(self.xml_handle.root_element,'WORKSHEET')
        for worksheet_node in worksheet_nodes:
            worksheet_name = self.xml_handle.get_attribute(worksheet_node,'NAME')
            ws_child_nodes = self.xml_handle.get_child_nodes(worksheet_node)
            for child_node in ws_child_nodes:
                item = SourceItem()
                item.name = self.xml_handle.get_attribute(child_node,'NAME')
                item.tag = self.xml_handle.get_attribute(child_node,'TAG')
                if item.tag == '':
                    item.tag = '--'
                item.value = self.xml_handle.get_attribute(child_node,'VALUE')
                if worksheet_name == 'fci':
                    item.media_type = MediaType.FCI
                elif worksheet_name == 'internal':
                    item.media_type = MediaType.INTERNAL
                elif worksheet_name == 'recordcontact':
                    item.media_type = MediaType.CONTACT
                elif worksheet_name == 'recordcontactless':
                    item.media_type = MediaType.CONTACTLESS
                else:
                    Log.info('Unkonwn worksheet name.')
                self.source_items.append(item)
        return self.source_items

# 万事达1156表格专用类            
class Form1156:
    def __init__(self,tablename):
        self.excel = ExcelOp(tablename)
        self.source_items = []

    def _filter_data(self,data):
        if isinstance(data,int):
            return str(data)
        #过滤掉单引号，双引号和空格及None值
        if not data or data.strip() == 'NOT PRESENT' or data.strip() == 'N/A':
            return None 
        data = data.strip()
        if data[0] == '"' or data[0] == "'":
            data = data[1:len(data) - 1].strip()
        return data

    def _handle_tag_value(self,data):
        self_define_list = ['Determined by issuer','Data preparation']
        if data in self_define_list:
            return ''   #处理DP自定义数据
        if utils.is_hex_str(data):
            return data
        return utils.str_to_bcd(data)

    def print_unused_data(self):
        print('====================1156 form unused tag list====================')
        for item in self.source_items:
            if not item.used:
                print("%-20s||%-10s||%-60s||%-100s" % (item.media_type.name,item.tag,item.value,item.name))

    def get_data(self,tag,media_type,desc=None):
        for item in self.source_items:
            if item.media_type == media_type and item.tag == tag:
                item.used = True
                return item.value
        return None
                
    def get_data_by_desc(self,desc,media_type):
        '''
        某些MCA数据没有标签一栏，可以通过desc描述找到对应的tag值，
        前提是模板中已经有对应的comment字符串
        '''
        for item in self.source_items:
            if item.media_type == media_type and item.name == desc:
                item.used = True
                return item.value
        return None

    def _get_data(self,media_type,start_row,start_col,ignore_list=None,end_flag=None):
        for row in range(start_row,200):
            item = SourceItem()
            item.media_type = media_type
            item.name = self.excel.read_cell_value(row,start_col)
            item.name = self._filter_data(item.name)
            if not item.name:
                continue   
            if end_flag and end_flag in item.name:
                break
            else:
                if "All rights reserved" in item.name:
                    break   #说明已经遍历到了尽头

            item.tag = self.excel.read_cell_value(row,start_col + 1)
            if ignore_list and item.tag in ignore_list:
                continue    #模板直接忽略
            item.len = self.excel.read_cell_value(row,start_col + 2)
            item.value = self._filter_data(self.excel.read_cell_value(row,start_col + 3))
            if not item.value:
                continue    #过滤空值
            # item.value = self._handle_tag_value(item.value)
            if item.name == 'Length Of ICC Public Key Modulus': #处理ICC公钥长度问题
                if item.value == '1152':
                    item.value = '90'
                elif item.value == '1024':
                    item.value = '80'
            if item.value:
                item.tag = str(item.tag)
                print("%-20s||%-10s||%-60s||%-100s" % (str(item.media_type),item.tag,item.value,item.name))
                self.source_items.append(item)
                if item.tag == '84':
                    item4F = item
                    item4F.tag = '4F'
                    self.source_items.append(item4F)
        return self.source_items
    
    # 处理FCI数据
    def get_fci_data(self,sheet_name='FCI (1)',start_row=5,start_col=2):
        if self.excel.open_worksheet(sheet_name):
            header = self.excel.read_cell_value(start_row,start_col)
            if str(header).strip() != 'Data object name':
                Log.info('can not get fci header')
                return None
            start_row += 2
            ignore_template_list = ['6F','A5','BF0C']
            self.fci_data = self._get_data(MediaType.FCI,start_row,start_col,ignore_template_list)
        return self.fci_data

    def get_internal_data(self,sheet_name='MCA data objects (1)',start_row=5,start_col=2):
        if self.excel.open_worksheet(sheet_name):
            header = self.excel.read_cell_value(start_row,start_col)
            if str(header).strip() != 'Data object name':
                Log.info('can not get fci header')
                return None
            start_row += 1
            self.internal_data = self._get_data(MediaType.INTERNAL,start_row,start_col)
        return self.internal_data

    def get_mag_data(self,sheet_name='Records (1)',start_row=5,start_col=2):
        if self.excel.open_worksheet(sheet_name):
            header = self.excel.read_cell_value(start_row,start_col)
            if str(header).strip() != 'Contactless mag-stripe data':
                Log.info('can not get mag header')
                return None
            start_row += 3
            self.mag_data = self._get_data(MediaType.MAGSTRIPE,start_row,start_col + 2,None,'Data object name')
        return self.mag_data

    def get_contactless_data(self,sheet_name='Records (1)',start_row=18,start_col=2):
        if self.excel.open_worksheet(sheet_name):
            header = self.excel.read_cell_value(start_row,start_col)
            if str(header).strip() != 'Contactless EMV data':
                Log.info('can not get contactless header')
                return None
            start_row += 3
            self.contactless_data = self._get_data(MediaType.CONTACTLESS,start_row,start_col + 2,None,'Data object name')
        return self.contactless_data

    def get_contact_data(self,sheet_name='Records (1)',start_row=43,start_col=2):
        if self.excel.open_worksheet(sheet_name):
            header = self.excel.read_cell_value(start_row,start_col)
            if str(header).strip() != 'Contact EMV data':
                Log.info('can not get contact header')
                return None
            start_row += 3
            self.contact_data = self._get_data(MediaType.CONTACT,start_row,start_col + 2,None,'Data object name')
        return self.contact_data

    def get_shared_data(self,sheet_name='Records (1)',start_row=77,start_col=2):
        if self.excel.open_worksheet(sheet_name):
            header = self.excel.read_cell_value(start_row,start_col)
            if str(header).strip() != 'Shared data':
                Log.info('can not get fci header')
                return None
            start_row += 3
            self.shared_data = self._get_data(MediaType.SHARED,start_row,start_col + 2)
        return self.shared_data
    
    def read_data(self):
        Log.info('====================1156 form tag list====================')
        self.get_fci_data()
        self.get_internal_data()
        self.get_contact_data()
        self.get_contactless_data()
        self.get_mag_data()
        self.get_shared_data()
        return self.source_items

class ImportForm:
    def _get_value(self,items,tag,media,name):
        has_found = False
        value = ''
        if tag in ('D9','94'): # AFL 不从MC原始数据中获取
            return ''
        if tag == 'D8': # goldpac Form中定义了D8为非接，但原始数据中的D8在internal数据中
            media = ''
        for item in items:
            if media: # 若有传入media,则需要比对media
                if item.tag.strip() == tag.strip() and item.media_type == media.lower():
                    item.used = True
                    value = item.value
                    has_found = True
                    break
            else:
                if item.tag.strip() == tag.strip():
                    item.used = True
                    value = item.value
                    has_found = True
                    break
        
        if not has_found: # 如果通过tag和media无法找到，则通过name查找
            for item in items:
                if item.name.strip() == name.strip():
                    item.used = True
                    value = item.value
                    break
        return value

    def write(self,items,goldpac_form,sheet_name,start_row=5,start_col=2):
        excel = ExcelOp(goldpac_form)
        if excel.open_worksheet(sheet_name):
            first_header = excel.read_cell_value(start_row,start_col)
            if str(first_header).strip() != 'Data Category':
                print('can not found form start position')
                return None
            start_row += 1 #默认标题行之后就是数据行
            for row in range(start_row,200):
                name = excel.read_cell_value(row,start_col + 1)
                tag = excel.read_cell_value(row,start_col + 2)
                if not tag:
                    break
                tag = str(tag).strip()
                value = str(excel.read_cell_value(row,start_col + 5)).strip()
                media = ''
                temp = tag.split('-')
                if len(temp) == 2:
                    tag = temp[0].strip()
                    media = temp[1].strip()
                item_value = self._get_value(items,tag,media,name)
                if not item_value:
                    Log.warn('can not find: tag:%s,   name:%s',tag,name)
                    item_value = 'N.A'
                if tag not in ('94','D9'):
                    excel.write_cell_value(row,start_col + 5,item_value)
            excel.save()

    def print_unsed_item(self,items):
        Log.info('no used tag list at first application----------------------------')
        for item in items:
            if not item.used:
                Log.info("tag:{0:6s} |value:{1:30s}|name:{2}".format(item.tag,item.value,item.name))

class GenItoDoc:
    def __init__(self,dp_xml,ito_docx):
        self.dp_xml = dp_xml    #DP xml配置文件
        self.ito_docx = ito_docx
        cwd = os.path.dirname(__file__)
        ito_docx_template = os.path.join(cwd,'template','DpRequirement.docx')
        self.docx = Docx(ito_docx_template)
        self.xml_handle = XmlParser(dp_xml,XmlMode.READ)

    def _parse_rule(self,app_node,dgi_node):
        rule = ''
        dgi_name = self.xml_handle.get_attribute(dgi_node,'name')
        # 处理个人化需加密的DGI
        if dgi_name in settings.encrypt_dgi_rules[0]:
            rule += '\n' + settings.encrypt_dgi_rules[1]
        # 处理个人化RSA秘钥规则
        if dgi_name in settings.rsa_dgi_rules[0]:
            cert_node = self.xml_handle.get_first_node(app_node,'Cert')
            if not cert_node:
                Log.error('can not handle rsa rule, cert node is not existed.')
            else:
                rsa_len = self.xml_handle.get_attribute(cert_node,'rsa')
                rule += '\n' +  (settings.rsa_dgi_rules[1]).format(rsa_len)

        # 处理DGI的值为固定值的规则
        if dgi_name in settings.fixed_value_rules[0]:
            dgi_value = ''
            tag_nodes = self.xml_handle.get_nodes(dgi_node,'Tag')
            for tag_node in tag_nodes:
                name = self.xml_handle.get_attribute(tag_node,'name')
                tag_type = self.xml_handle.get_attribute(tag_node,'type')
                value = self.xml_handle.get_attribute(tag_node,'value')
                tag_format = self.xml_handle.get_attribute(tag_node,'format')
                if tag_format == 'V':
                    dgi_value += value
                else:
                    if tag_type != 'fixed' or name == '--':
                        Log.error('can not construct dgi value, make sure tag type is fixed and name not equal --')
                        break
                    # TLV格式
                    dgi_value += name + utils.get_strlen(value) + value
            rule += '\n' +  (settings.fixed_value_rules[1].format(dgi_value))

        # 处理kcv规则
        for kcv_dgi_name,compared_dgi_name in settings.kcv_check_rules[0]:
            if kcv_dgi_name == dgi_name:
                rule += '\n' +  (settings.kcv_check_rules[1].format(compared_dgi_name,kcv_dgi_name))
                break
        
        # 处理tag相关的规则
        tag_nodes = self.xml_handle.get_nodes(dgi_node,'Tag')
        for tag_node in tag_nodes:
            tag_name = self.xml_handle.get_attribute(tag_node,'name')
            # 处理空值规则
            if tag_name in settings.empty_tag_rules[0]:
                rule += '\n' +  (settings.empty_tag_rules[1].format(tag_name))
                break
        if rule.startswith('\n'):
            rule = rule[1:]
        return rule

    def gen_ito_docx(self):
        app_nodes = self.xml_handle.get_child_nodes(self.xml_handle.root_element,'App')
        for app_node in app_nodes:
            # 添加应用分组标题
            aid = self.xml_handle.get_attribute(app_node,'aid')
            self.docx.add_heading(2,'应用分组 Aid:' + aid)

            # 添加表格,初始值为1行3列
            col_count = 3
            new_table = self.docx.add_table(1,col_count)

            # 设置表格标题栏
            title = ['标签','数据来源','备注']
            for col in range(col_count): #设置表格头部栏
                cell = self.docx.get_cell(new_table,0,col)
                self.docx.set_cell_background(cell,'FFCA00')
                self.docx.set_cell_text(cell,title[col])

            # 设置每个应用的DGI分组
            dgi_nodes = self.xml_handle.get_child_nodes(app_node,'DGI')
            for dgi_node in dgi_nodes:
                new_row = new_table.add_row()
                dgi_name = self.xml_handle.get_attribute(dgi_node,'name')
                # 设置第一列
                self.docx.set_cell_text(new_row.cells[0],dgi_name)
                self.docx.set_cell_background(new_row.cells[0],'FFCA00')
                # 设置第二列
                content = '从制卡数据DGI' + dgi_name + '中获取'
                self.docx.set_cell_text(new_row.cells[1],content)
                # 设置第三列
                rule = self._parse_rule(app_node,dgi_node)
                self.docx.set_cell_text(new_row.cells[2],rule)
            self.docx.save_as(self.ito_docx)

# 根据dp xml文件生成Word文档DP需求
class GenDpDoc:
    def __init__(self,dp_xml,dp_docx):
        self.dp_xml = dp_xml    #DP xml配置文件
        self.dp_docx = dp_docx
        cwd = os.path.dirname(__file__)
        dp_docx_template = os.path.join(cwd,'template','DpRequirement.docx')
        self.docx = Docx(dp_docx_template)
        self.xml_handle = XmlParser(dp_xml,XmlMode.READ)

    def _get_deep_template_count(self,dgi_node):
        '''
        获取DGI节点中最深模板的个数，用于确定表格需要创建多少列
        '''
        if not dgi_node:
            return 0
        children_nodes = self.xml_handle.get_child_nodes(dgi_node,'Template')
        if not children_nodes:
            return 0
        return 1 + max(self._get_deep_template_count(child) for child in children_nodes)

    def _get_template_child_tags_count(self,template_node):
        '''
        获取模板中Tag子节点的个数
        '''
        tag_nodes = self.xml_handle.get_child_nodes(template_node,'Tag')
        if tag_nodes:
            return len(tag_nodes)
        return 0

    def _get_node_level(self,root_node,child_node):
        level = 0
        parent = self.xml_handle.get_parent(child_node)
        while parent and parent != root_node:
            parent = self.xml_handle.get_parent(parent)
            level += 1
        return level

    def _get_children_nodes(self,parent_node,nodes):
        '''
        获取父节点下的所有子节点
        '''
        # name = self.xml_handle.get_attribute(parent_node,'name')
        # if name:
        #     print('name:' + name)
        children_nodes = self.xml_handle.get_child_nodes(parent_node)
        for child_node in children_nodes[:]:
            # print(self.xml_handle.get_attribute(child_node,'name'))
            nodes.append(child_node)
            self._get_children_nodes(child_node,nodes)



    def _create_table(self,dgi_node):
        # 若DGI包含70模板，则不将70模板包含到表格中(过滤70模板)
        dgi_child_nodes = self.xml_handle.get_child_nodes(dgi_node)
        if dgi_child_nodes and len(dgi_child_nodes) == 1:
            name = self.xml_handle.get_attribute(dgi_child_nodes[0],'name')
            if name and name == '70': 
                dgi_node = dgi_child_nodes[0]
        col_count = self._get_deep_template_count(dgi_node) + 5
        new_table = self.docx.add_table(1,col_count)
        # 设置表格标题栏
        title = ['' for empty in range(col_count - 5)] + ['标签','数据元','长度','格式','值']
        for col in range(col_count): #设置表格头部栏
            cell = self.docx.get_cell(new_table,0,col)
            self.docx.set_cell_background(cell,'FFCA00')
            self.docx.set_cell_text(cell,title[col])
        # 如果包含非70模板，需要合并标题栏中的Tag列
        if col_count > 5:
            cells = []
            for col in range(col_count - 4):
                cells.append(self.docx.get_cell(new_table,0,col))
            self.docx.merge_cell(cells)
        # 设置表格中每个单元格的内容
        # 设置每个tag标签
        dgi_child_nodes = []
        self._get_children_nodes(dgi_node,dgi_child_nodes)
        for tag_node in dgi_child_nodes:
            tag_comment = self.xml_handle.get_attribute(tag_node,'comment')
            tag_name = self.xml_handle.get_attribute(tag_node,'name')
            if tag_name == 'FFFF':
                tag_name = '--'
                tag_comment = '--'
            tag_value = self.xml_handle.get_attribute(tag_node,'value')
            tag_type = self.xml_handle.get_attribute(tag_node,'type')
            tag_format = self.xml_handle.get_attribute(tag_node,'format')
            tag_eq = self.xml_handle.get_attribute(tag_node,'replace_equal_by_D')
            tag_ascii = self.xml_handle.get_attribute(tag_node,'convert_ascii')
            if not tag_value:
                tag_value = ''
            if tag_type == 'fixed' and not tag_value:
                tag_value = 'Empty'
            if tag_type == 'kms':
                tag_value = 'From KMS'
            if tag_eq and tag_eq == 'true':
                tag_value += '-EQ'
            if tag_ascii and tag_ascii == 'true':
                tag_value += '-ASCII'
            
            if not tag_comment:
                tag_comment = ''
            new_row = new_table.add_row()
            level = self._get_node_level(dgi_node,tag_node)
            self.docx.set_cell_text(new_row.cells[level],tag_name)
            self.docx.set_cell_text(new_row.cells[-4],tag_comment) #数据元在倒数第4列描述
            if tag_value and utils.is_hex_str(tag_value):
                self.docx.set_cell_text(new_row.cells[-3],utils.get_strlen(tag_value))
            else:
                self.docx.set_cell_text(new_row.cells[-3],'var') #长度在倒数第3列描述
            self.docx.set_cell_text(new_row.cells[-2],tag_format) # 倒数第二列为V,TLV
            if tag_name == '9F10':
                uat = tag_value[2:4]
                tag_value = tag_value[0:2] + '(DKI)' + tag_value[4:]
                live = self.xml_handle.get_attribute(tag_node,'live')
                tag_value += '\nUAT DKI:' + uat + '\nLIVE DKI:' + live
                self.docx.set_cell_text(new_row.cells[-1],tag_value) #值为最后一列
            else:
                self.docx.set_cell_text(new_row.cells[-1],tag_value) #值为最后一列

    def gen_dp_docx(self):
        app_maps = {
            'A0000000041010':'MC Advance 应用分组',
            '315041592E5359532E4444463031':'PSE应用分组',
            '325041592E5359532E4444463031':'PPSE应用分组',
            'A000000333010101':'UICS/PBOC 借记应用分组',
            'A000000333010102':'UICS/PBOC 贷记应用分组',
            'A0000000031010':'Visa 应用分组',
            'A00000047400000001':'Jetco 应用分组',
            'A000000025010402':'Amex应用分组',
            'A000000025010900':'Amex辅助应用分组',
        }
        app_nodes = self.xml_handle.get_child_nodes(self.xml_handle.root_element,'App')
        pse_node = self.xml_handle.get_first_node(self.xml_handle.root_element,'PSE')
        ppse_node = self.xml_handle.get_first_node(self.xml_handle.root_element,'PPSE')
        if pse_node:
            app_nodes.append(pse_node)
        if ppse_node:
            app_nodes.append(ppse_node)
        for app_node in app_nodes:
            # 添加应用分组标题
            aid = self.xml_handle.get_attribute(app_node,'aid')
            self.docx.add_heading(2,app_maps.get(aid,'应用分组 Aid:' + aid))
            # 设置每个应用的DGI分组
            dgi_nodes = self.xml_handle.get_child_nodes(app_node,'DGI')
            for dgi_node in dgi_nodes:
                dgi_name = self.xml_handle.get_attribute(dgi_node,'name')
                dgi_comment = self.xml_handle.get_attribute(dgi_node,'comment')
                dgi_title = 'DGI-{0}:{1}'.format(dgi_name,dgi_comment)
                template70_node = self.xml_handle.get_first_node(dgi_node,'Template')
                if template70_node:
                    name = self.xml_handle.get_attribute(template70_node,'name')
                    if name == '70':
                        dgi_title = '[需添加70模板]' + dgi_title
                self.docx.add_heading(3,dgi_title)
                self._create_table(dgi_node)
            self.docx.save_as(self.dp_docx)


class DpTemplateXml:
    def __init__(self,app_type='',name=''):
        self.app_type = app_type
        self.name = name

class GenDpXml:
    '''
    根据xml模板、Excel表格中的数据、emboss file中的数据生成DP XML配置文件
    '''
    config = dict() #一个类属性字典，用于自定义配置
    def __init__(self,template_xml,first_source_items,second_source_items=None,file_items=None):
        # 支持默认DP模板配置和自定义模板
        if isinstance(template_xml,DpTemplateXml):
            cwd = os.path.dirname(__file__)
            template_xml_path = os.path.join(cwd,'template',template_xml.app_type.lower(),template_xml.name)
            self.template_xml = template_xml_path
        else:
            self.template_xml = template_xml # 自定义模板
        self.template_handle = XmlParser(self.template_xml)
        self.first_source_items = first_source_items # 第一应用数据集
        self.second_source_items = second_source_items # 第二应用下的数据
        self.cur_source_items = self.first_source_items # 表示当前应用使用的数据集
        self.unused_data = []

        
    def _get_aid_from_excel(self,source_item):
        '''
        根据Excel表中的tag4F获取aid
        '''
        for item in source_item:
            if item.tag == '4F':
                return item.value

    def _parse_value(self,value):
        '''
        分析Excel表中value列
        '''
        tag_item = TagInfo()
        item = value.split('-')
        if item:
            tag_item.value = item[0]
            for data in item[1:]:
                if data.strip() == 'ASCII':
                    tag_item.convert_to_ascii = True
                if data.strip() == 'EQ':
                    tag_item.replace_equal_by_D = True
                if data.strip() == 'TRIM':
                    tag_item.trim_right_space = True
                if data.strip() == 'BCD':
                    tag_item.convert_to_bcd = True
        return tag_item
        
    def _is_second_app(self,xml_handle,app_node):
        '''
        判断当前应用是否为第二应用
        '''
        aid = xml_handle.get_attribute(app_node,'aid')
        return aid == self._get_aid_from_excel(self.second_source_items)

    def _get_source_item(self,tag='',source='',comment=''):
        '''
        从数据集cur_source_items中查找对应的数据
        '''
        if tag and source:  # 根据模板xml中的tag和type来查找数据
            for item in self.cur_source_items:
                if source.lower() == 'kms': #对于来自kms,仅需要比对tag
                    if tag == item.tag:
                        return item
                else: #对于其他tag,需要认清是contact还是contactless
                    if tag == item.tag and source.lower() == item.media_type.lower():
                        return item
        #有时候需要根据模板xml中的comment来查找tag数据
        # 如果根据tag和source仍找不到，则可以通过comment查找
        if comment:   
            for item in self.cur_source_items:
                if item.name and item.name.strip() == comment.strip():
                    return item
        return None

    def _get_dp_item(self,tag='',source='',comment=''):
        source_item = self._get_source_item(tag,source,comment)
        if source_item:
            source_item.used = True
            dp_item = self._parse_value(source_item.value)
            if source_item.tag == 'Rsa_len':
                rsa = int(dp_item.value)
                dp_item.value = utils.int_to_hex_str(rsa // 8)
            dp_item.tag = tag
            if source_item.data_type == 'kms':
                dp_item.source = 'kms'
            else:
                dp_item.source = source
            dp_item.comment = comment
            return dp_item
        return None

    def _get_rsa_len(self):
        item = self._get_source_item('Rsa_len','contact')
        if item:
            item.used = True
            return item.value
        return None

    def _get_cert_expiry_date(self,xml_handle,app_node):
        expiry_date = ''
        tag5F24_node = xml_handle.get_node_by_attribute(app_node,'Tag',name='5F24')
        if tag5F24_node:
            tag5F24 = xml_handle.get_attribute(tag5F24_node,'value')
            if tag5F24.find('{') != -1:
                if tag5F24.count('[') == 1:
                    first_start_mark = tag5F24.find('[')
                    first_end_mark = tag5F24.find(']')
                    start,end = tag5F24[first_start_mark + 1:first_end_mark].split(',')
                    start_pos = int(start)
                    end_pos = int(end)
                    mm_start = str(end_pos - 1)
                    yy_end = str(start_pos + 1)
                    expiry_date = '[{0},{1}][{2},{3}]'.format(mm_start,end,start,yy_end)
                elif tag5F24.count('[') == 2:
                    first_start_mark = tag5F24.find('[')
                    first_end_mark = tag5F24.find(']')
                    second_start_mark = tag5F24.rfind('[')
                    second_end_mark = tag5F24.rfind(']')
                    expiry_date = tag5F24[second_start_mark:second_end_mark] + tag5F24[first_start_mark:first_end_mark + 1]
                else:
                    Log.info('special expiry date of tag5F24, please manually set expiry date of cert')
            else:
                Log.info('special expiry date of tag5F24, please manually set expiry date of cert')
        return expiry_date

    def output_result(self):
        Log.warn('no used tag list at first application')
        for item in self.first_source_items:
            if not item.used:
                Log.warn("tag:{0:15s} |value:{1:40s}|desc:{2}".format(item.tag,item.value,item.name))
        if self.second_source_items:
            Log.warn('\n\nno used tag list at second application')
            for item in self.second_source_items:
                if not item.used:
                    Log.warn("tag:{0:15s} |value:{1:40s}|desc:{2}".format(item.tag,item.value,item.name))
        Log.warn('\n\nno used tag list at template')
        ignore_tag_list = ['8000','8001','9000','9001','A006','A016','8401','8400','8201','8202','8203','8204','8205']
        for data in self.unused_data:
            if data[0] not in ignore_tag_list:
                Log.warn("tag:{0:15s} |source:{1:40s}|desc:{2}".format(data[0],data[1],data[2]))        

    def _add_alias(self,xml_handle,tag_nodes):
        '''
        给重复的tag添加别名(唯一的ID名称)，例如tag为--或其他重复tag
        '''
        for index,tag_node in enumerate(tag_nodes):
            attr_tag = xml_handle.get_attribute(tag_node,'name')
            attr_value = xml_handle.get_attribute(tag_node,'value')
            attr_comment = xml_handle.get_attribute(tag_node,'comment') #将comment属性放到最后
            xml_handle.remove_attribute(tag_node,'comment')
            if attr_tag == '--':
                alias = get_alias()
                xml_handle.set_attribute(tag_node,'alias',alias)
                xml_handle.set_attribute(tag_node,'comment',attr_comment)
                continue
            has_diff_value_at_prev_section = False
            for cur_index,cur_tag_node in enumerate(tag_nodes):
                cur_tag = xml_handle.get_attribute(cur_tag_node,'name')
                cur_attr_value = xml_handle.get_attribute(cur_tag_node,'value')
                if has_diff_value_at_prev_section and index <= cur_index:
                    has_diff_value_at_prev_section = False # 重置该标记
                    # 如果上半区遍历完
                    alias = xml_handle.get_attribute(cur_tag_node,'alias')
                    if not alias: # 若不存在相同值的tag,才增加别名，若存在相同的值，这alias肯定已经赋值了
                        alias = get_alias()
                        xml_handle.set_attribute(tag_node,'alias',alias)
                        xml_handle.set_attribute(tag_node,'comment',attr_comment)
                        break
                if cur_tag == attr_tag:
                    if index > cur_index:  # 搜寻此tag上半区的Tag节点
                        if attr_value == cur_attr_value: #若发现有值相同的tag,若存在别名，取该别名
                            cur_attr_alias = xml_handle.get_attribute(cur_tag_node,'alias')
                            if cur_attr_alias:
                                xml_handle.set_attribute(tag_node,'alias',cur_attr_alias)
                                xml_handle.set_attribute(tag_node,'comment',attr_comment)
                                break
                        else: #若发现不同的值，需要先做个标记，等上半区遍历完再下结论
                            has_diff_value_at_prev_section = True
                        # xml_handle.set_attribute(tag_node,'comment',attr_comment)
                    elif index < cur_index: #搜寻此tag下半区的Tag节点
                        if attr_value != cur_attr_value: 
                            alias = get_alias()
                            xml_handle.set_attribute(tag_node,'alias',alias)
                            xml_handle.set_attribute(tag_node,'comment',attr_comment)
                            break 
                    else:
                        xml_handle.set_attribute(tag_node,'comment',attr_comment)

    def _delete_empty_template(self,new_xml_handle,parent_node):
        '''
        如果模板节点下面没有tag节点，则需要删除该模板节点
        '''
        child_template_nodes = new_xml_handle.get_child_nodes(parent_node,'Template')
        for child_template_node in child_template_nodes: #同级的template
            tag_nodes = new_xml_handle.get_child_nodes(child_template_node,'Tag')
            if not tag_nodes:
                new_xml_handle.remove(child_template_node)
            else:
                self._delete_empty_template(new_xml_handle,child_template_node)

    def remove_empty_node(self,new_xml_handle):
        app_nodes = new_xml_handle.get_child_nodes(new_xml_handle.root_element,'App')
        for app_node in app_nodes:
            dgi_nodes = new_xml_handle.get_child_nodes(app_node,'DGI')
            for dgi_node in dgi_nodes:
                self._delete_empty_template(new_xml_handle,dgi_node)
                dgi_child_nodes = new_xml_handle.get_child_nodes(dgi_node)
                if not dgi_child_nodes:
                    dgi_name = new_xml_handle.get_attribute(dgi_node,'name')
                    new_xml_handle.remove(dgi_node)
                    Log.warn('Remove DGI: %s',dgi_name)

    def _handle_9F4B(self,new_xml_handle,app_node):
        rsa_len = self._get_rsa_len()
        if self.config.get('dgi_9F4B') and int(rsa_len) > 1024:
            dgi_of_tag9F4B = int(self.config.get('dgi_9F4B'),16)
            dgi_nodes = new_xml_handle.get_nodes(app_node,'DGI')
            before_node = None
            for dgi_node in dgi_nodes:
                dgi_name = new_xml_handle.get_attribute(dgi_node,'name')
                if dgi_name and utils.is_hex_str(dgi_name):
                    int_dgi = int(dgi_name,16)
                    if int_dgi < dgi_of_tag9F4B:
                        before_node = dgi_node
                    else:
                        new_node = new_xml_handle.create_node('DGI')
                        new_xml_handle.set_attribute(new_node,'name',self.config.get('dgi_9F4B'))
                        attr = dict()
                        attr['name'] = 'FFFF'
                        attr['format'] = 'V'
                        attr['type'] = 'fixed'
                        
                        if not rsa_len:
                            rsa_len = self.config.get('rsa','1152')
                        rsa = int(rsa_len)
                        str_rsa = utils.int_to_hex_str(rsa // 8)
                        str_rsa = '9F4B81' + str_rsa
                        str_tlv_len = utils.int_to_hex_str(rsa // 8 + 4)
                        value = '7081' + str_tlv_len + str_rsa
                        attr['value'] = value
                        new_xml_handle.add_node(new_node,'Tag',**attr)
                        new_xml_handle.insert_before(app_node,new_node,before_node)     
                        break  

    def _handle_9F10(self,tag,source):
        source_item = self._get_source_item(tag,source)
        dp_item = TagInfo()
        value = source_item.value
        index_start = value.find('[')
        index_mid = value.find('|')
        index_end = value.find(']')
        dp_item.value = value[0:index_start] + value[index_start + 1:index_mid] + value[index_end + 1:]
        dp_item.live = value[index_mid + 1:index_end]
        if source_item:
            source_item.used = True
            dp_item.tag = tag
            dp_item.source = source
        return dp_item
   
    def _get_afls(self,tag94):
        dgi_list = []
        afls = utils.parse_afl(tag94)
        for afl in afls:
            dgi_list.append(utils.int_to_hex_str(afl.sfi) + utils.int_to_hex_str(afl.record_no))
        return dgi_list

    def _get_sig_dgi(self,tag94):
        afls = utils.parse_afl(tag94)
        for afl in afls:
            if afl.is_static_sign_data:
                return utils.int_to_hex_str(afl.sfi) + utils.int_to_hex_str(afl.record_no)
        return ''

    def gen_xml(self,new_xml,char_set='UTF-8'):
        # 复制模板
        fpath,_ = os.path.split(new_xml)    #分离文件名和路径
        if not os.path.exists(fpath):
            os.makedirs(fpath)
        shutil.copyfile(self.template_xml,new_xml)      #复制文件
        dp_xml_handle = XmlParser(new_xml, XmlMode.READ_WRITE)

        # 设置应用节点属性，需要设置aid
        app_nodes = dp_xml_handle.get_child_nodes(dp_xml_handle.root_element,'App')
        if app_nodes:
            aid = self._get_aid_from_excel(self.first_source_items)
            dp_xml_handle.set_attribute(app_nodes[0],'aid',aid)
            dp_xml_handle.set_attribute(app_nodes[0],'type',self.config.get('app_type').lower())
            if len(app_nodes) == 2: #支持双应用
                aid = self._get_aid_from_excel(self.second_source_items)
                dp_xml_handle.set_attribute(app_nodes[1],'aid',aid)
                dp_xml_handle.set_attribute(app_nodes[1],'type',self.config.get('second_app_type').lower())


        # 1. 设置bin号
        bin_node = dp_xml_handle.get_first_node(dp_xml_handle.root_element,'Bin')
        if bin_node:
            dp_xml_handle.set_attribute(bin_node,'value',self.config.get('card_bin',''))

        # 将pse,ppse节点也加入到app节点集合中，设置tag属性
        pse_node = dp_xml_handle.get_first_node(dp_xml_handle.root_element,'PSE')
        ppse_node = dp_xml_handle.get_first_node(dp_xml_handle.root_element,'PPSE')
        if pse_node: #防止特殊应用,没有pse或ppse节点的情况
            app_nodes.append(pse_node)
        if ppse_node:
            app_nodes.append(ppse_node)

        # 设置Tag节点
        for index, app_node in enumerate(app_nodes):
            aid = dp_xml_handle.get_attribute(app_node,'aid')

            contact_tag94 = ''
            contactless_tag94 = ''
            sig_dgis = []
            
            tag_nodes = dp_xml_handle.get_nodes(app_node,'Tag') #取应用下面的Tag节点
            for tag_node in tag_nodes:
                attr_tag        = dp_xml_handle.get_attribute(tag_node,'name')        # Tag标签
                attr_source     = dp_xml_handle.get_attribute(tag_node,'source')   # Tag来源 contact,contactless,fci...
                attr_format     = dp_xml_handle.get_attribute(tag_node,'format')   # Tag 形式,TLV,V结构
                attr_comment    = dp_xml_handle.get_attribute(tag_node,'comment') # Tag描述信息
                attr_sig_id     = dp_xml_handle.get_attribute(tag_node,'sig_id')   # Tag使用的签名数据
                attr_value      = dp_xml_handle.get_attribute(tag_node,'value')     # Tag值
                second_app      = dp_xml_handle.get_attribute(tag_node,'second_app') # 指定是否使用第二应用数据

                parent_node = dp_xml_handle.get_parent(tag_node)   # 获取tag所在的DGI节点
                dgi_name    = dp_xml_handle.get_attribute(parent_node,'name') # DGI节点名称


                # 生成数据,需要设置当前使用的数据集合(是第一个应用还是第二个应用的集合)
                if self._is_second_app(dp_xml_handle,app_node) or (second_app and second_app == 'true'):
                    self.cur_source_items = self.second_source_items
                else:
                    self.cur_source_items = self.first_source_items

                # 删除之，重新给属性排序
                dp_xml_handle.remove_attribute(tag_node,'type')
                dp_xml_handle.remove_attribute(tag_node,'comment')
                dp_xml_handle.remove_attribute(tag_node,'format')
                dp_xml_handle.remove_attribute(tag_node,'source')
                dp_xml_handle.remove_attribute(tag_node,'sig_id')
                dp_xml_handle.remove_attribute(tag_node,'value')
                
                # value属性获取规则如下:
                # 1. 若模板中有值，则优先从模板中取值
                # 2. 若模板无value属性，则根据模板中的name和source属性从source_items集合中获取
                # 3. 若模板无value属性，且name属性为--,则根据comment属性从source_items集合中获取
                # 注意，这里的value还只是固定值,value属性放置在type属性之后设置
                tag_item = TagInfo()
                tag_item.value = attr_value #模板中的值
                if not tag_item.value:
                    # 若tag为--,则根据comment获取值
                    if not attr_tag or attr_tag.strip() == '--':
                        tag_item = self._get_dp_item(comment=attr_comment)
                    else:
                        # 根据tag和source获取值
                        if attr_tag == '9F10':
                            tag_item = self._handle_9F10(tag=attr_tag, source=attr_source)
                        else:
                            tag_item = self._get_dp_item(tag=attr_tag, source=attr_source)
                tags_from_kms = ('8F','9F32','8000','8001','9000','9001','8400','8401','A006','A016','90','92','93','9F46','9F47', '9F48','8201','8202','8203','8204','8205','DC','DD')
                
                # 对 App key做特殊处理
                if dgi_name in ('8000','9000','8001','9001','A006','A016','8400','8401'):
                    attr_tag = dgi_name
                
                # 过滤无法从excel表中中查找到的数据且不是证书相关数据
                if not tag_item and attr_tag not in tags_from_kms:
                    dp_xml_handle.remove(tag_node)
                    self.unused_data.append((attr_tag,attr_source,attr_comment))
                    continue

                # 记录每个应用的AFL, 用于在comment 中添加那些分组是用于接触/非接
                if attr_tag == '94' and attr_source == 'contact':
                    contact_tag94 = tag_item.value
                elif attr_tag in ('94','D9') and attr_source == 'contactless':
                    contactless_tag94 = tag_item.value

                # 对于visa项目,如果RSA长度小于等于1024,需要在9116,9117中添加9F4B81XX
                # 注意,这里默认visa为第一应用,若出现visa为第二应用的情况，则不适用。
                #这里使用特殊的tagFFFF表示DGI9116,9117中的TL结构
                if aid == 'A0000000031010' and attr_tag == 'FFFF' and dgi_name in ('9116','9117'):
                    rsa_len = self._get_rsa_len()
                    if not rsa_len:
                        rsa_len = self.config.get('rsa')
                    if not rsa_len:
                        Log.error('can not get rsa information from template xml')
                    else:
                        rsa = int(rsa_len)
                        if  rsa <= 1024: 
                            tag_item.value += '9F4B81' + utils.int_to_hex_str(rsa // 8)

                # 来自加密机, 优先处理从加密机里面的数据，不取来自客户表中数据
                # 有些attr_tag为--,但也有可能是证书相关的信息，所以再根据tag_item中的source属性进行判断
                if attr_tag in tags_from_kms or (tag_item.source and tag_item.source == 'kms'):
                    dp_xml_handle.set_attribute(tag_node,'type','kms')
                elif tag_item.value: 
                    # 设置type类型
                    if tag_item.value.find('[') != -1 or tag_item.value.find('{') != -1:
                        dp_xml_handle.set_attribute(tag_node,'type','file') #说明数据来自文件
                    else:
                        dp_xml_handle.set_attribute(tag_node,'type','fixed') #说明是固定值
                    # 设置value值
                    if tag_item.value.strip().lower() == 'empty':
                        dp_xml_handle.set_attribute(tag_node,'value','')
                    elif tag_item.value == 'N.A':
                        if aid == 'A0000000031010' and tag_item.tag == '82':
                            Log.warn('remove DGI %s',dgi_name)
                            dp_xml_handle.remove(parent_node)
                            continue
                        else:
                            dp_xml_handle.remove(tag_node)
                            self.unused_data.append((attr_tag,attr_source,attr_comment))
                    elif tag_item.tag == '9F10':
                        dp_xml_handle.set_attribute(tag_node,'value',tag_item.value)
                        dp_xml_handle.set_attribute(tag_node,'live',tag_item.live)
                    else:
                        dp_xml_handle.set_attribute(tag_node,'value',tag_item.value)

                    # 设置tag属性
                    if tag_item.convert_to_ascii:
                        dp_xml_handle.set_attribute(tag_node,'convert_ascii','true')
                    if tag_item.replace_equal_by_D:
                        dp_xml_handle.set_attribute(tag_node,'replace_equal_by_D','true')
                    if tag_item.trim_right_space:
                        dp_xml_handle.set_attribute(tag_node,'trim_right_space','true')
                    if tag_item.convert_to_bcd:
                        dp_xml_handle.set_attribute(tag_node,'convert_bcd','true')
                else:
                    dp_xml_handle.remove(tag_node)
                    self.unused_data.append((attr_tag,attr_source,attr_comment))
                
                # 设置签名,直接复制模板中的值
                if attr_sig_id:
                    dp_xml_handle.set_attribute(tag_node,'sig_id',attr_sig_id)

                #设置编码格式和描述，若模板中没有comment属性，则取至settings.py
                dp_xml_handle.set_attribute(tag_node,'format',attr_format)
                if not attr_comment:
                    attr_comment = settings.get_mappings_info(aid,attr_tag).desc
                dp_xml_handle.set_attribute(tag_node,'comment',attr_comment)

            #对于VISA应用，如果RSA长度大于1024,需要新增DGI存储tag9F4B
            if aid == 'A0000000031010':
                config_node = dp_xml_handle.get_first_node(app_node,"Config")
                if config_node:
                    attr_dgi_9F4B = dp_xml_handle.get_attribute(config_node,'dgi_9F4B')
                    attr_dgi_GPO_AAC = dp_xml_handle.get_attribute(config_node,'dgi_qgpo_aac')
                    self.config['dgi_9F4B'] = attr_dgi_9F4B
                    self.config['dgi_qgpo_aac'] = attr_dgi_GPO_AAC
                self._handle_9F4B(dp_xml_handle,app_node)
                # 处理dgi_GPO_AAC节点
                if self.config['dgi_qgpo_aac']:
                    dgi_GPO_AAC_node = dp_xml_handle.get_node_by_attribute(app_node,"DGI",name=self.config['dgi_GPO_ACC'])
                    dgi_9115_node = dp_xml_handle.get_node_by_attribute(app_node,"DGI",name='9115')
                    if dgi_9115_node:
                        tag94_node = dp_xml_handle.get_node_by_attribute(dgi_9115_node,"Tag",name='94')
                        if not tag94_node:
                            dp_xml_handle.remove(dgi_GPO_AAC_node)
                    
            #最后设置alias
            self._add_alias(dp_xml_handle,tag_nodes) 
            # 删除 空模板节点
            self.remove_empty_node(dp_xml_handle)
            if aid == 'A0000000041010': #对于mc应用，如果不支持磁条交易，需删除DGI8400和DGI8401
                node_dgi_0101 = dp_xml_handle.get_node_by_attribute(app_node,'DGI',name="0101")
                if not node_dgi_0101:
                    node_dgi_8400 = dp_xml_handle.get_node_by_attribute(app_node,'DGI',name="8400")
                    node_dgi_8401 = dp_xml_handle.get_node_by_attribute(app_node,'DGI',name="8401")
                    if node_dgi_8400:
                        dp_xml_handle.remove(node_dgi_8400)
                    if node_dgi_8401:
                        dp_xml_handle.remove(node_dgi_8401)
            # 给comment属性添加 contact/contactless和signature单词
            dgi_nodes = dp_xml_handle.get_nodes(app_node,'DGI')
            contact_dgi_names = self._get_afls(contact_tag94)
            contactless_dgi_names = self._get_afls(contactless_tag94)
            sig_dgis.append(self._get_sig_dgi(contact_tag94))
            sig_dgis .append(self._get_sig_dgi(contactless_tag94))
            for dgi_node in dgi_nodes:
                attr_comment = dp_xml_handle.get_attribute(dgi_node,'comment')
                attr_name = dp_xml_handle.get_attribute(dgi_node,'name')
                if int(attr_name,16) < 0x0A01:
                    attr_comment = 'SFI ' + attr_name[0:2] + ' Record ' + attr_name[2:]
                    flag = False
                    if attr_name in contact_dgi_names and attr_name not in contactless_dgi_names:
                        attr_comment += ' (contact'
                        flag = True
                    elif attr_name in contactless_dgi_names and attr_name not in contact_dgi_names:
                        attr_comment += ' (contactless'
                        flag = True
                    if attr_name in sig_dgis:
                        attr_comment += ',signature'
                        flag = True
                    if flag:
                        attr_comment += ')'

                if not attr_comment:
                    attr_comment = settings.get_mappings_info(aid,attr_name).desc
                dp_xml_handle.set_attribute(dgi_node,'comment',attr_comment)

            # 配置完所有tag节点之后配置证书信息
            if aid not in ('315041592E5359532E4444463031','325041592E5359532E4444463031'):
                #设置证书配置信息
                cert_nodes = dp_xml_handle.get_nodes(app_node,'Cert')
                if cert_nodes:
                    expiry_date = self._get_cert_expiry_date(dp_xml_handle,app_node)
                    for cert_node in cert_nodes:
                        # 双应用公用失效日期
                        if self.config.get('expireDate'):
                            dp_xml_handle.set_attribute(cert_node,'expireDate',self.config.get('expireDate'))
                        else:
                            dp_xml_handle.set_attribute(cert_node,'expireDate',expiry_date)
                        dp_xml_handle.set_attribute(cert_node,'expireDateType',self.config.get('expireDateType','file'))
                        rsa_len = self._get_rsa_len()
                        if rsa_len:
                            dp_xml_handle.set_attribute(cert_node,'rsa',rsa_len)
                        else:
                            if index == 1: #第二应用,若双应用RSA长度一致，则只需设置一个RSA，默认长度为1152位
                                dp_xml_handle.set_attribute(cert_node,'rsa',self.config.get('second_rsa',self.config.get('rsa','1152')))
                            else:
                                dp_xml_handle.set_attribute(cert_node,'rsa',self.config.get('rsa','1152'))
                
        # 设置完毕后，保存
        dp_xml_handle.save(char_set)

#根据DP xml文件和emboss file模拟一条制卡数据，用于制作测试卡
class MockCps:
    '''
    根据xml配置文件及emboss file模拟生成CPS格式的测试卡数据
    '''
    def __init__(self,xml_file,emboss_file,process_emboss_file_module=None):
        self.cps = Cps()
        self.cps.dp_file_path = xml_file
        self.xml_handle = XmlParser(xml_file)
        self.process_emboss_file_module = process_emboss_file_module
        if emboss_file:
            self.emboss_file_handle = FileHandle(emboss_file,'r+')

    def _assemble_value(self,tag,data,data_format):
        '''
        根据data_format组装TLV数据
        '''
        if data_format == 'TLV':
            return utils.assemble_tlv(tag,data)
        else:
            return data

    def _get_date_value(self,date):
        '''
        解析tag5F24/5F25格式
        '''
        if len(date) < 5:
            if date in (r'{FD}',r'{LD}'):
                date = time.strftime('%y%m') + date
            else:
                Log.error('len of date is too short')
                return None
        yy = date[0:2]
        mm = date[2:4]
        dd_flag = date[4:]
        if not yy.isdigit():
            Log.error('handle value:%s',date)
            Log.error('date of yy is incorrected format')
            return None
        if not mm.isdigit() or int(mm) > 12 or int(mm) == 0:
            Log.error('handle value:%s',date)
            Log.error('date of mm is incorrected format')
            return None
        if dd_flag == r'{FD}':
            return yy + mm + '01'
        if dd_flag == r'{LD}':
            if mm in ('01','03','05','07','08','10','12'):
                return yy + mm + '31'
            elif mm in ('04','06','09','11'):
                return yy + mm + '30'
            else:
                return yy + mm + '28'
        return None

    def _get_value_from_file(self,value):
        '''
        解析emboss items中数据数据
        '''
        data = ''
        index = 0
        while index < len(value):
            start_index = str(value).find('[',index)
            if start_index == -1:
                data += value[index:]
                break
            else:
                data += value[index:start_index]
            end_index = str(value).find(']',start_index)
            pos_str = value[start_index + 1:end_index]
            start_pos = int(pos_str.split(',')[0])
            end_pos = int(pos_str.split(',')[1])
            data += self.emboss_file_handle.read_pos(start_pos,end_pos)
            index = end_index + 1
        if r'{FD}' in data or r'{LD}' in data:
            return self._get_date_value(data)
        return data

    def _parse_tag_value(self,tag_node,kms=None):
        attrs = self.xml_handle.get_attributes(tag_node)
        tag = attrs['name']
        value = ''
        value_type = attrs['type']
        value_format = attrs['format']
        if value_type == 'fixed': #处理固定值
            value = self._assemble_value(tag,attrs['value'],value_format)
        elif value_type == 'kms':   #处理KMS生成的数据
            if not kms:
                Log.info('kms is not inited. can not process tag %s with kms type',tag)
            else:
                kms_tag = tag
                if 'sig_id' in attrs:
                    kms_tag = kms_tag + '_' + attrs['sig_id']
                value = self._assemble_value(tag,kms.get_value(kms_tag),value_format)
        elif value_type == 'file': # 处理文件数据
            value = self.xml_handle.get_attribute(tag_node,'value')
            if value is not None:
                if value:
                    value = self._get_value_from_file(value)
                trim_right_space = self.xml_handle.get_attribute(tag_node,'trim_right_space')
                if trim_right_space:
                    value = value.rstrip()
                replaceD = self.xml_handle.get_attribute(tag_node,'replace_equal_by_D')
                if replaceD:
                    value = value.replace('=','D')
                convert_ascii = self.xml_handle.get_attribute(tag_node,'convert_ascii')
                if convert_ascii and convert_ascii.lower() == 'true':
                    value = utils.str_to_bcd(value)
                convert_bcd = self.xml_handle.get_attribute(tag_node,'convert_bcd')
                if convert_bcd and convert_bcd.lower() == 'true':
                    value = utils.bcd_to_str(value)
                if not value:
                    Log.info('tag%s value is empty',tag)
                if len(value) % 2 != 0:
                    value += 'F'
                value = self._assemble_value(tag,value,value_format)
            else: #如果类型为file的Tag,没有value属性，则通过emboss file模块处理值
                if self.process_emboss_file_module:
                    mod_obj = importlib.import_module(self.process_emboss_file_module)
                    if mod_obj:
                        if hasattr(mod_obj,'process_tag' + tag):
                            func = getattr(mod_obj,'process_tag' + tag)
                            value = self._assemble_value(tag,func(),value_format)
                        else:
                            Log.info('can not process tag%s',tag)
                else:
                    Log.info('emboss file module can not process tag%s',tag)
        return tag,value
        
    def _parse_template(self,template_node,kms=None):
        template_value = ''
        template = self.xml_handle.get_attribute(template_node,'name')
        child_nodes = self.xml_handle.get_child_nodes(template_node)
        for child_node in child_nodes:
            if child_node.nodeName == 'Tag':
                _,value = self._parse_tag_value(child_node,kms)
                template_value += value
            elif child_node.nodeName == 'Template':
                template_value += self._parse_template(child_node,kms)
        return utils.assemble_tlv(template,template_value)

    def _gen_sig_data(self,app_node,kms):
        sig_nodes = self.xml_handle.get_nodes(app_node,'Sig')
        for sig_node in sig_nodes:
            sig_data = ''
            sig_id = self.xml_handle.get_attribute(sig_node,'id')
            tag_nodes = self.xml_handle.get_child_nodes(sig_node,'Tag')
            tag5A = ''
            for tag_node in tag_nodes:
                    tag,value = self._parse_tag_value(tag_node,kms)
                    sig_data += value
                    if tag == '5A':
                        tag5A = value[4:]
            if tag5A == '':
                Log.error
                tag5A = kms.issuer_bin + '0000000001'
            Log.info('gen new icc cert input:')
            Log.info('5A:%s',tag5A)
            Log.info('sig_data:%s',sig_data)
            kms.gen_new_icc_cert(tag5A,sig_data,sig_id)
            kms.gen_new_ssda(kms.issuer_bin,sig_data,sig_id)

    def _get_first_bin(self):
        '''
        从DP xml文件中的Bin节点，取第一个Bin号生成测试数据
        '''
        issuer_bin = ''
        bin_node = self.xml_handle.get_first_node(self.xml_handle.root_element,'Bin')
        if bin_node:
            issuer_bin = self.xml_handle.get_attribute(bin_node,'value')
            if not issuer_bin or issuer_bin == '':
                Log.error('Please provide card Bin number, if not, card will use default Bin number:654321')
                issuer_bin = '654321'
            else:
                issuer_bin = issuer_bin.split(',')[0]    #取第一个bin号生成证书
        return issuer_bin

    def _get_rsa_len(self,app_node):
        '''
        从DP xml文件中的指定App节点中的Cert节点获取RSA长度
        '''
        rsa_len = 1024
        cert_node = self.xml_handle.get_first_node(app_node,'Cert')
        if cert_node:
            rsa_len_str = self.xml_handle.get_attribute(cert_node,'rsa')
            if not rsa_len_str or rsa_len_str == '':
                Log.error('Please provide card ICC RSA length, if not, card will use default RSA len:1024')
            else:
                rsa_len = int(rsa_len_str)       
        return rsa_len

    def _process_dgi(self,dgi_node,kms=None):
        dgi = Dgi()
        dgi.name = self.xml_handle.get_attribute(dgi_node,'name')
        if dgi.name in ('8000','9000','8001','9001','A006','A016','8400','8401'):
            dgi.append_tag_value(dgi.name,kms.get_value(dgi.name))
            return dgi
        child_nodes = self.xml_handle.get_child_nodes(dgi_node)
        if child_nodes and len(child_nodes) == 1:   #判断是否为70模板开头，若是，则忽略掉70模板
            attr_name = self.xml_handle.get_attribute(child_nodes[0],'name')
            if attr_name == '70':
                child_nodes = self.xml_handle.get_child_nodes(child_nodes[0])
        for child_node in child_nodes:
            if child_node.nodeName == 'Tag':
                tag,value = self._parse_tag_value(child_node,kms)
                value = value.replace(' ','') #过滤掉value中的空格
                data_format = self.xml_handle.get_attribute(child_node,'format')
                if data_format == 'V':  #对于value数据，取dgi作为tag
                    dgi.append_tag_value(dgi.name,value)
                else:
                    dgi.add_tag_value(tag,value)
            elif child_node.nodeName == 'Template':
                # 对于非70模板，直接拼接该值，不做TLV解析处理
                template_value = self._parse_template(child_node,kms)
                dgi.append_tag_value(dgi.name,template_value)
            else:
                Log.error('unrecognize node%s',child_node.nodeName)
        if dgi.name == '0101' and dgi.is_existed('56') and dgi.is_existed('9F6B'):
            # 说明是MC应用，且支持MSD,这时需要生成对应的DC,DD
            tag56 = dgi.get_value('56')[4:] # 偷懒，不需要解析TLV
            tag9F6B = dgi.get_value('9F6B')[6:]
            kms.gen_mc_cvc3(tag56,tag9F6B)
        return dgi

    def _process_pse(self,pse_node):
        pse = Dgi()
        pse.name = pse_node.nodeName
        dgi_nodes = self.xml_handle.get_child_nodes(pse_node)
        for dgi_node in dgi_nodes:
            dgi = self._process_dgi(dgi_node)
            for key,value in dgi.tag_value_dict.items():
                pse.add_tag_value(key,value)
        return pse

    def gen_cps(self):
        Log.info('Start generate cps data...')
        app_nodes = self.xml_handle.get_nodes(self.xml_handle.root_element,'App')
        for app_count,app_node in enumerate(app_nodes):
            aid = self.xml_handle.get_attribute(app_node,'aid')
            Log.info('\nhandle aid: %s',aid)
            if app_count == 0:
                self.cps.first_app_aid = aid
            elif app_count == 1:
                self.cps.second_app_aid = aid
            Log.info('init kms...')
            issuer_bin = self._get_first_bin()
            rsa_len = self._get_rsa_len(app_node)
            Log.info('issuer bin:%s',issuer_bin)
            Log.info('rsa len:%s',rsa_len)
            kms = Kms()
            kms.init(issuer_bin,rsa_len)
            self._gen_sig_data(app_node,kms)    #根据sig节点生成与证书相关的数据
            dgi_nodes = self.xml_handle.get_child_nodes(app_node,"DGI") #获取app节点下所有的DGI节点
            for dgi_node in dgi_nodes:
                dgi = self._process_dgi(dgi_node,kms)
                if app_count > 0:   # 说明是双应用，DGI形式为[0101_2]
                    dgi.name = dgi.name + '_' + str(app_count + 1)
                self.cps.add_dgi(dgi)
            kms.close()
        # 处理PSE 和 PPSE
        pse_node = self.xml_handle.get_first_node(self.xml_handle.root_element,'PSE')
        if pse_node:
            pse_aid = self.xml_handle.get_attribute(pse_node,'aid')
            self.cps.pse_aid = pse_aid
            pse_dgi = self._process_pse(pse_node)
            self.cps.add_dgi(pse_dgi)
        ppse_node = self.xml_handle.get_first_node(self.xml_handle.root_element,'PPSE')
        if ppse_node:
            ppse_aid = self.xml_handle.get_attribute(ppse_node,'aid')
            self.cps.ppse_aid = ppse_aid
            ppse_dgi = self._process_pse(ppse_node)
            self.cps.add_dgi(ppse_dgi)
        return self.cps

if __name__ == '__main__':
    docx = GenDpDoc('D://DP.xml','D://DP需求.docx')
    docx.gen_dp_docx()
