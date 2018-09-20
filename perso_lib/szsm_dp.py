from perso_lib.file_handle import FileHandle
from perso_lib.rule_file import RuleFile
from perso_lib.cps import Cps,Dgi
from perso_lib import data_parse
from perso_lib import utils
from perso_lib.rule import Rule

def process_tlv(data):
    item_list = []
    items = data.split('|')
    items_count = len(items)
    for index in range(0,items_count,3):
        if index + 3 > items_count:
            break
        tag = items[index]
        length = items[index + 1]
        value = items[index + 2]
        item_list.append((tag,length,value))
    return item_list

def process_data(data,data_type):
    dgi = Dgi()
    dgi.dgi = data_type
    item_list = process_tlv(data)
    for item in item_list:
        dgi.add_tag_value(item[0],item[2])
    return dgi

def process_EF02(cps):
    data_ef02 = ''
    for item in cps.dgi_list:
        if item.dgi == '01':
            data_ef02 = item.get_value('EF02')
    data_ef02 = data_ef02[8:]   #EF02总长度
    for i in range(8):
        bcd_item_len = data_ef02[0 : 8]
        n_item_len = int(utils.bcd_to_str(bcd_item_len)) * 2
        value = data_ef02[8 : 8 + n_item_len]
        data_ef02 = data_ef02[8 + n_item_len :]
        dgi = Dgi()
        if i == 3:
            dgi.dgi = '8205'
            dgi.add_tag_value(dgi.dgi,value)
            cps.add_dgi(dgi)
        elif i == 4:
            dgi.dgi = '8204'
            dgi.add_tag_value(dgi.dgi,value)
            cps.add_dgi(dgi)
        elif i == 5:
            dgi.dgi = '8203'
            dgi.add_tag_value(dgi.dgi,value)
            cps.add_dgi(dgi)
        elif i == 6:
            dgi.dgi = '8202'
            dgi.add_tag_value(dgi.dgi,value)
            cps.add_dgi(dgi)
        elif i == 7:
            dgi.dgi = '8201'
            dgi.add_tag_value(dgi.dgi,value)
            cps.add_dgi(dgi)
    return cps

def process_rule(rule_file_name,cps):
    rule = Rule(cps)
    rule_file = RuleFile(rule_file_name)
    add_tag_nodes = rule_file.get_nodes(rule_file.root_element,'AddTag')
    for node in add_tag_nodes:
        attrs = rule_file.get_attributes(node)
        if 'srcTag' not in attrs:
            attrs['srcTag'] = attrs['dstTag']
        rule.process_add_tag(attrs['srcDGI'],attrs['srcTag'],attrs['dstDGI'],attrs['dstTag'])
    merge_tag_nodes = rule_file.get_nodes(rule_file.root_element,'MergeTag')
    for node in merge_tag_nodes:
        attrs = rule_file.get_attributes(node)
        rule.process_merge_tag(attrs['srcDGI'],attrs['srcTag'],attrs['dstDGI'],attrs['dstTag'])   
    fixed_tag_nodes = rule_file.get_nodes(rule_file.root_element,'AddFixedTag')
    for node in fixed_tag_nodes:
        attrs = rule_file.get_attributes(node)
        rule.process_add_fixed_tag(attrs['srcDGI'],attrs['tag'],attrs['value'])
    decrypt_nodes = rule_file.get_nodes(rule_file.root_element,'Decrypt')
    for node in decrypt_nodes:
        decrypt_attrs = rule_file.get_attributes(node)
        rule.process_decrypt(decrypt_attrs['DGI'],decrypt_attrs['key'],decrypt_attrs['type'])
    kcv_nodes = rule_file.get_nodes(rule_file.root_element,'AddKcv')
    for node in kcv_nodes:  #需放在解密之后执行
        attrs = rule_file.get_attributes(node)
        rule.process_add_kcv(attrs['srcDGI'],attrs['dstDGI'],attrs['type'])
    exchange_nodes = rule_file.get_nodes(rule_file.root_element,'Exchange')
    for node in exchange_nodes:
        exchange_attrs = rule_file.get_attributes(node)
        rule.process_exchange(exchange_attrs['srcDGI'],exchange_attrs['exchangedDGI'])
    assmble_tlv_nodes = rule_file.get_nodes(rule_file.root_element,'AssembleTlv')
    for node in assmble_tlv_nodes:
        attrs = rule_file.get_attributes(node)
        rule.process_assemble_tlv(attrs['DGI'])
    remove_dgi_nodes = rule_file.get_nodes(rule_file.root_element,'RemoveDGI')
    for node in remove_dgi_nodes:
        attrs = rule_file.get_attributes(node)
        rule.process_remove_dgi(attrs['DGI'])
    remove_tag_nodes = rule_file.get_nodes(rule_file.root_element,'RemoveTag')
    for node in remove_tag_nodes:
        attrs = rule_file.get_attributes(node)
        rule.process_remove_tag(attrs['DGI'],attrs['tag'])
    return rule.cps

def process_szsm_dp(dp_file,rule_file):
    fh = FileHandle(dp_file,'r+')
    flag_dc = '[01]'
    flag_ec = '[02]'
    flag_q = '[03]'
    cps_list = []
    while True:
        cps = Cps()
        cps.dp_file_path = dp_file
        card_data = fh.read_line()
        if card_data == '': #数据处理完毕
            break
        index_dc = card_data.find(flag_dc)
        index_ec = card_data.find(flag_ec)
        index_q = card_data.find(flag_q)
        data_dc = card_data[index_dc + len(flag_dc) : index_ec]
        data_ec = card_data[index_ec + len(flag_ec) : index_q]
        data_q = card_data[index_q + len(flag_q) :]
        dgi_dc = process_data(data_dc,'01')
        dgi_ec = process_data(data_ec,'02')
        dgi_q = process_data(data_q,'03')
        cps.add_dgi(dgi_dc)
        cps.add_dgi(dgi_ec)
        cps.add_dgi(dgi_q)
        cps = process_EF02(cps)
        if rule_file is not None:
            process_rule(rule_file,cps)
        cps_list.append(cps)
    return cps_list



if __name__ == '__main__':
    cps_list = process_szsm_dp('./test_data/szsm.dp','./test_data/rule1.xml')
    for cps in cps_list:
        account = cps.get_account()
        path = 'D://' + account + 'txt'
        cps.save(path)