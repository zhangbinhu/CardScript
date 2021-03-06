
from enum import Enum

class App(Enum):
    PSE     = 0
    PPSE    = 1
    UICS    = 2
    VISA    = 3
    MCA     = 4
    JETCO   = 5

class LenType(Enum):
	Fixed = 0
	Range = 1

class TagMapInfo():
	tag = ''
	desc = ''
	len_type = None
	tag_len = []

def get_mappings_info(aid,tag):
	tag_map_info = TagMapInfo()
	tag_map_info.tag = tag
	mappings = None
	if aid == '315041592E5359532E4444463031':
		mappings = pse_tag_desc_mappings
	elif aid == '325041592E5359532E4444463031':
		mappings = ppse_tag_desc_mappings
	elif aid == 'A0000000031010':
		mappings = visa_tag_desc_mappings
	elif aid == 'A0000000041010':
		mappings = mc_tag_desc_mappings
	elif aid in ('A000000333010101','A000000333010102'):
		mappings = uics_tag_desc_mappings
	elif aid in ('A00000047400000001'):
		mappings = jetco_tag_desc_mappings
	if mappings:
		items = mappings.get(tag)
		if items:
			tag_map_info.desc = items[0]
			if len(items) > 1:
				tag_len = items[1]
				if '-' in tag_len:
					min_len = int(tag_len.split('-')[0])
					max_len = int(tag_len.split('-')[1])
					tag_map_info.len_type = LenType.Range
					tag_map_info.tag_len = [min_len,max_len]
				elif '|' in tag_len:
					str_lens = tag_len.split('|')
					lens = [int(str_len) for str_len in str_lens]
					tag_map_info.len_type = LenType.Fixed
					tag_map_info.tag_len = lens
					# return LenType.Fixed,lens
				else:
					tag_map_info.len_type = LenType.Fixed
					tag_map_info.tag_len = [int(items[1])]
					# return LenType.Fixed,[int(items[1])]
	return tag_map_info

encrypt_dgi_rules = (
	['8000','A006','A016'],
	'需要解密，个人化时需要使用个人化过程密钥加密'
)

rsa_dgi_rules = (
	['8201','8202','8203','8204','8205',],
	'检查RSA密钥长度是否为{0}位，如果不是则报错；需要解密，个人化时需要填充“80..00“，然后使用个人化过程密钥加密。'
)

kcv_check_rules = (
	[('9000','8000')],
	'使用DGI{0}的密钥分别对8字节0x00加密，分别取前3字节作为kcv，拼起来后与DGI{1}进行比较，如果不一致，则报错。'
)

fixed_value_rules = (
	['9104','A005'],
	'判断值是否为{0}'
)

empty_tag_rules = (
	['92','9F48'],
	'判断Tag{0}的长度是否为0，如果为0则不个人化'
)



visa_tag_desc_mappings = {
#Command Response Data-DGI
	'9104' : ('GPO Response Data for VSDC',),
	'9115' : ('GPO Response Data for qVSDC online decline without ODA',),
	'9116' : ('GPO Response Data for qVSDC offline with ODA',),
	'9117' : ('GPO Response Data for qVSDC online with ODA',),
	'9207' : ('GPO Response Data for qVSDC',),	
	'9200' : ('Issuer application data',),
	'9102' : ('SELECT Command Response for contact mode',),
	'9103' : ('SELECT Command Response for contactless mode',),
#Internal Data-DGI
	'3000' : ('Card internal risk management Data',),
	'3001' : ('Card internal risk management Data',),
	'3F55' : ('Contactless Counters Template',),
	'3F56' : ('Counter Data Template',),
	'3F57' : ('International Counter Template',),
	'3F58' : ('Amounts Data Template',),
	'3F5B' : ('Application Internal Data Template',),
#Key-DGI
	'8000' : ('DES keys',),
	'9000' : ('DES Key Check Values',),
	'8010' : ('PIN block',),
	'9010' : ('PIN Related Data(PTC/PTL)',),
	'8201' : ('ICC Key CRT constant q-1 mod p',),
	'8202' : ('ICC Key CRT constant d mod (q – 1)',),
	'8203' : ('ICC Key CRT constant d mod (p – 1)',),
	'8204' : ('ICC Key CRT constant prime factor q',),
	'8205' : ('ICC Key CRT constant prime factor p',),
#Template Data
	'70' : ('Record Template',),
	'61' : ('Application Template',),
	'A5' : ('FCI Proprietary Template',),
	'BF0C' : ('FCI Issuer Discretionary Data',),	
#FCI Data
	'4F' : ('AID','5-16'),
	'50' : ('Application Label','1-16'),
	'87' : ('Application Priority Indicator','1'),
	'5F2D' : ('Language Preference','2-8'),
	'9F38' : ('PDOL'),
	'9F11' : ('Issuer Code Table Index','1'),
	'9F12' : ('Application Preferred Name','1-16'),
	'9F4D' : ('Log Entry','2'),
	'5F55' : ('Issuer Country Code (alpha2)','2'),
	'5F56' : ('Issuer Country Code (alpha3)','3'),	
	'9F5A' : ('Program ID','5-16'),
#Record Data
	'57' : ('Track 2 Equivalent Data','1-19'),
	'9F1F' : ('Track 1 Discretionary Data',),
	'5F20' : ('Cardholder Name','2-26'),
	'5A' : ('PAN','1-10'),
	'5F24' : ('Application Expiration Date','3'),
	'5F25' : ('Application Effective Date','3'),
	'5F34' : ('Application PAN Sequence Number','1'),
	'9F07' : ('Application Usage Control','2'),
	'8E' : ('CVM List',),
	'9F0D' : ('IAC-Default','5'),
	'9F0E' : ('IAC-Denial','5'),
	'9F0F' : ('IAC-Online','5'),
	'5F28' : ('Issuer Country Code','2'),
	'9F4A' : ('Static Data Authentication Tag List','1'),
	'8C' : ('CDOL1',),
	'8D' : ('CDOL2',),
	'5F30' : ('Service Code','2'),
	'9F08' : ('Application Version Number','2'),
	'9F49' : ('DDOL',),
	'9F42' : ('Application Currency Code','2'),
	'9F44' : ('Application Currency Exponent','1'),
	'8F' : ('CA PKI','1'),
	'90' : ('IPK Certificate',),
	'92' : ('IPK Remainder',),
	'93' : ('Signed Static Application Data',),	'9F32' : ('IPK Exponent','1|3'),
	'9F46' : ('ICCPK Certificate',),
	'9F47' : ('ICCPK Exponent','1|3',),
	'9F48' : ('ICCPK Remainder',),
	'9F69' : ('Card authentication related data','5-16'),
	'9F4B' : ('Signed Dynamic Application Data',),
	'9F6E' : ('Form Factor Indicator','4'),
	'9F7C' : ('Customer Exclusive Data','1-32'),
#Internal Data
	'82' : ('AIP','2'),
	'94' : ('AFL',),
	'9F10' : ('Issuer Application Data',),
	'9F36' : ('Application Transaction Counter (ATC)','2'),
	'9F13' : ('Last Online ATC Register','2'),
	'9F4F' : ('Log Format',),
	'9F51' : ('Application Currency Code','2'),
	'9F52' : ('Application Default Action','4|6'),
	'9F53' : ('CTCIL','1'),
	'9F54' : ('CTTAL','6'),
	'9F56' : ('Issuer Authentication Indicator','1'),
	'9F57' : ('Issuer Country Code','2'),
	'9F58' : ('CTCL','1'),
	'9F59' : ('CTCUL','1'),
	'9F5C' : ('CTTAUL','6'),
	'9F5D' : ('Available Offline Spending Amount','1'),
	'9F5E' : ('CTIUL','1'),
	'9F68' : ('Card Additional Processes','4'),
	'9F6B' : ('CVM Limit','6'),
	'9F6C' : ('Card Transaction Qualifier','2'),
	'9F72' : ('CTCICL','1'),
	'9F73' : ('Currency Conversion Parameters','2'),
	'9F77' : ('VLP Funds Limit','6'),
	'9F78' : ('VLP Single Transaction Limit','6'),
	'9F79' : ('VLP Available Funds','6'),
}

mc_tag_desc_mappings = {
#Command Response Data-DGI
	'A005' : ('Get Processing Options Response(Contact)',),
	'B005' : ('Get Processing Options Response(Contactless)',),
	'9102' : ('SELECT Response Data',),
	
#Internal Data-DGI
	'A002' : ('Common Risk Management Parameters',),
	'A004' : ('Public Key Length',),
	'A012' : ('Risk Management Parameters(Contact)',),
	'A013' : ('Application Control(Contact)',),
	'A014' : ('Read Record Filter(Contact)',),
	'A015' : ('Card Issuer Action Codes(Contact)',),
	'A022' : ('Risk Management Parameters(Contactless)',),
	'A023' : ('Application Control(Contactless)',),
	'A024' : ('Read Record Filter(Contactless)',),
	'A025' : ('Card Issuer Action Codes(Contactless)',),
	'A007' : ('Application Status and ATC Limit',),
	'A017' : ('3DES Key Information(Contact)',),
	'A027' : ('3DES Key Information(Contactless)',),
	'A009' : ('Application Life Cycle Data',),
	'A00E' : ('Data Storage Configuration',),
	'B002' : ('Transaction log related data',),	'B100' : ('Contact Relay Resistance Protocol Parameters',),
	'B101' : ('Contactless Relay Resistance Protocol Parameters',),
	'B102' : ('Linked Application Index',),
	'B023' : ('Contactless IVCVC3',),
	'B011' : ('Protected Data Envelope 1',),
	'B012' : ('Protected Data Envelope 2',),
	'B013' : ('Protected Data Envelope 3',),
	'B014' : ('Protected Data Envelope 4',),
	'B015' : ('Protected Data Envelope 5',),
	'B016' : ('Unprotected Data Envelopes 1',),
	'B017' : ('Unprotected Data Envelopes 2',),
	'B018' : ('Unprotected Data Envelopes 3',),
	'B019' : ('Unprotected Data Envelopes 4',),
	'B01A' : ('Unprotected Data Envelopes 5',),	
#Key-DGI
	'8000' : ('Contact Keyset',),
	'9000' : ('DES Key Check Values(Contact)',),
	'8001' : ('Contactless Keyset',),
	'9001' : ('DES Key Check Values(Contactless)',),
	'A006' : ('Contact ICC Dynamic Number Master Key',),
	'A016' : ('Contactless ICC Dynamic Number Master Key',),
	'8401' : ('Contactless KDCVC3',),
	'8010' : ('Reference PIN Block',),
	'9010' : ('PIN Related Data',),
	'8201' : ('ICC Private Key CRT constant q-1 mod p',),
	'8202' : ('ICC Private Key CRT constant d mod(q-1)',),
	'8203' : ('ICC Private Key CRT constant d mod(p-1)',),
	'8204' : ('ICC Private Key CRT constant prime factor q',),
	'8205' : ('ICC Private Key CRT constant prime factor p',),
#Template Data
	'70' : ('Record Template',),
	'61' : ('Application Template',),
	'A5' : ('FCI Proprietary Template',),
	'BF0C' : ('FCI Issuer Discretionary Data',),	
#FCI Data
	'4F' : ('AID','5-16'),
	'50' : ('Application Label','1-16'),
	'87' : ('Application Priority Indicator','1'),
	'5F2D' : ('Language Preference','2-8'),
	'9F38' : ('PDOL',),
	'9F11' : ('Issuer Code Table Index','1'),
	'9F12' : ('Application Preferred Name','1-16'),
	'9F4D' : ('Log Entry','2'),
	'9F5D' : ('Application Capabilities information','3'),
	'9F0A' : ('Application Selection Registered Proprietary Data',),
	'5F55' : ('Issuer Country Code(alpha2 format)','2'),
	'42' : ('Issuer Identification Number','3'),
	'9F5E' : ('DS ID','8-11'),
	'9F6E' : ('Third Party Data','5-32'),	
#Record Data
	'56' : ('Track 1 Data','1-76'),
	'9F62' : ('PCVC3 TRACK1','2'),
	'9F63' : ('PUNATC TRACK1','6'),
	'9F64' : ('NATC TRACK1','1'),
	'9F65' : ('PCVC3 TRACK2','2'),
	'9F66' : ('PUNATC TRACK2','2'),
	'9F67' : ('NATC TRACK2','1'),
	'9F6B' : ('Track 2 Data','1-19'),
	'9F6C' : ('MagStripe Application Version Number','2'),

	'57' : ('Track 2 Equivalent Data','1-19'),
	'9F1F' : ('Track 1 Discretionary Data',),
	'5F20' : ('Cardholder Name','2-26'),
	'5A' : ('PAN','1-10'),
	'5F24' : ('Application Expiration Date','3'),
	'5F25' : ('Application Effective Date','3'),
	'5F34' : ('Application PAN Sequence Number','1'),
	'9F07' : ('Application Usage Control','2'),
	'8E' : ('CVM List',),
	'9F0D' : ('IAC-Default','5'),
	'9F0E' : ('IAC-Denial','5'),
	'9F0F' : ('IAC-Online','5'),
	'5F28' : ('Issuer Country Code','2'),
	'9F4A' : ('Static Data Authentication Tag List','1'),
	'8C' : ('CDOL1',),
	'8D' : ('CDOL2',),
	'5F30' : ('Service Code','2'),
	'9F08' : ('Application Version Number','2'),
	'9F49' : ('DDOL',),
	'9F42' : ('Application Currency Code','2'),
	'9F44' : ('Application Currency Exponent','1'),
	'8F' : ('CA Index','1'),
	'90' : ('IPK Certificate',),
	'92' : ('IPK Remainder',),
	'93' : ('Signed Static Application Data',),	'9F32' : ('IPK Exponent','1|3'),
	'9F46' : ('ICCPK Certificate',),
	'9F47' : ('ICCPK Exponent','1|3'),
	'9F48' : ('ICCPK Remainder',),
	'9F51' : ('DRDOL(Contactless)','3'),
	'9F5B' : ('DSDOL(Contactless)','12'),
	'9F55' : ('Issuer Authentication Flags(Contact)','1'),
	'9F56' : ('Issuer Proprietary Bitmap(Contact)',),
}

amex_tag_desc_mappings = {
#Command Response Data-DGI
	'9104' : ('GPO Response Data for contact',),
	'9105' : ('GPO Response Data for EMV contactless',),
	'9106' : ('GPO Response Data for Magnetic stripe contactless',),
	'9200' : ('Issuer application data',),
	'9300' : ('Issuer application data for EMV contactless',),
	'9400' : ('Issuer application data for Magnetic stripe contactless',),	
	'9102' : ('SELECT Command Response for contact mode',),
	'9103' : ('SELECT Command Response for contactless mode',),
#Internal Data-DGI
	'0D01' : ('Internal data',),
	'3001' : ('Internal data contactless',),
	'90B0' : ('Record Data Object Link',),
	'9090' : ('Data sharing',),	
#Key-DGI
	'8000' : ('DES keys',),
	'9000' : ('DES Key Check Values',),
	'8080' : ('DES keys for EMV contactless',),
	'9080' : ('DES Key Check Values for EMV contactless',),
	'8088' : ('DES keys for Magnetic stripe contactless',),
	'9088' : ('DES Key Check Values for Magnetic stripe contactless',),
	'8010' : ('PIN block',),
	'9010' : ('PIN Related Data(PTC/PTL)',),
	'8201' : ('ICC Key CRT constant q-1 mod p',),
	'8202' : ('ICC Key CRT constant d mod (q – 1)',),
	'8203' : ('ICC Key CRT constant d mod (p – 1)',),
	'8204' : ('ICC Key CRT constant prime factor q',),
	'8205' : ('ICC Key CRT constant prime factor p',),
#Template Data
	'70' : ('Record Template',),
	'61' : ('Application Template',),
	'A5' : ('FCI Proprietary Template',),
	'BF0C' : ('Issuer Discretionary Data',),
	'C0' : ('Interface data object',),
#FCI Data
	'4F' : ('AID','5-16'),
	'50' : ('Application Label','1-16'),
	'87' : ('Application Priority Indicator','1'),
	'5F2D' : ('Language Preference','2-8'),
	'9F38' : ('PDOL'),
	'9F11' : ('Issuer Code Table Index','1'),
	'9F12' : ('Application Preferred Name','1-16'),
	'9F4D' : ('Log Entry','2'),
	'9F0A' : ('Application Specific Registered Proprietary Data',),
#Record Data
	'57' : ('Track 2 Equivalent Data','1-19'),
	'9F1F' : ('Track 1 Discretionary Data','1-16'),
	'5F20' : ('Cardholder Name','2-26'),
	'5A' : ('PAN','1-10'),
	'5F24' : ('Application Expiration Date','3'),
	'5F25' : ('Application Effective Date','3'),
	'5F34' : ('Application PAN Sequence Number','1'),
	'9F07' : ('Application Usage Control','2'),
	'8E' : ('CVM List'),
	'9F0D' : ('IAC-Default','5'),
	'9F0E' : ('IAC-Denial','5'),
	'9F0F' : ('IAC-Online','5'),
	'5F28' : ('Issuer Country Code','2'),
	'9F4A' : ('Static Data Authentication Tag List','1'),
	'8C' : ('CDOL1',),
	'8D' : ('CDOL2',),
	'5F30' : ('Service Code','2'),
	'9F08' : ('Application Version Number','2'),
	'9F49' : ('DDOL','1-32'),
	'9F42' : ('Application Currency Code','2'),
	'9F44' : ('Application Currency Exponent','1'),
	'8F' : ('CA PKI','1'),
	'90' : ('IPK Certificate',),
	'92' : ('IPK Remainder',),
	'9F32' : ('IPK Exponent','1|3'),
	'9F46' : ('ICCPK Certificate',),
	'9F47' : ('ICCPK Exponent','1|3',),
	'9F48' : ('ICCPK Remainder',),
#Internal Data
	'82' : ('AIP','2'),
	'94' : ('AFL',),
	'9F10' : ('Issuer Application Data',),
	'DF03' : ('Application Default Action','2'),
	'9F36' : ('Application Transaction Counter (ATC)','2'),
	'9F13' : ('Last Online ATC Register','2'),
	'9F58' : ('LCOL','1'),
	'9F59' : ('UCOL','1'),
	'9F54' : ('CTTALL','6'),
	'9F62' : ('CTTAUL','6'),
	'9F53' : ('NDCTL','1'),
	'9F50' : ('ADCC','2'),
	'9F51' : ('CTTALLDC','6'),
	'9F52' : ('CTTAULDC','6'),
	'9F55' : ('NDUCOL','1'),
	'9F60' : ('CTTALL','6'),
	'9F61' : ('CTTAUL','6'),
	'9F63' : ('NDCTL','1'),
	'9F64' : ('STVUL','6'),
	'9F65' : ('STVULDC','6'),
	'9F68' : ('NDCTUL','1'),
	'9F69' : ('NDTTALLDC','6'),
	'9F6C' : ('CTTAULDC','6'),
}

jetco_tag_desc_mappings = {
#Command Response Data-DGI
	'9104' : ('GPO Response Data',),
	'9200' : ('Issuer application data',),
	'9102' : ('SELECT Command Response',),
#Internal Data-DGI
	'0D01' : ('Card internal risk management Data',),
	'0E01' : ('Card internal risk management Data',),
#Key-DGI
	'8000' : ('DES keys',),
	'9000' : ('DES Key Check Values',),
	'8010' : ('PIN block',),
	'9010' : ('PIN Related Data(PTC/PTL)',),
	'8201' : ('ICC Key CRT constant q-1 mod p',),
	'8202' : ('ICC Key CRT constant d mod (q – 1)',),
	'8203' : ('ICC Key CRT constant d mod (p – 1)',),
	'8204' : ('ICC Key CRT constant prime factor q',),
	'8205' : ('ICC Key CRT constant prime factor p',),
#Jetco-DGI
	'7FF1' : ('Jetco Data Object List 1',),
	'7FF2' : ('Jetco Data Object List 2',),
	'7FF3' : ('Jetco Data Object',),
	'7FF4' : ('Jetco Data Object',),
	'7FF5' : ('Jetco Data Object',),#Template Data
	'70' : ('Record Template',),
	'61' : ('Application Template',),
	'A5' : ('FCI Proprietary Template',),
	'BF0C' : ('FCI Issuer Discretionary Data',),	
#FCI Data
	'4F' : ('AID','5-16'),
	'50' : ('Application Label','1-16'),
	'87' : ('Application Priority Indicator','1'),
	'5F2D' : ('Language Preference','2-8'),
	'9F38' : ('PDOL',),
	'9F11' : ('Issuer Code Table Index','1'),
	'9F12' : ('Application Preferred Name','1-16'),
	'9F4D' : ('Log Entry','2'),
#Record Data
	'57' : ('Track 2 Equivalent Data','1-19'),
	'9F1F' : ('Track 1 Discretionary Data',),
	'5F20' : ('Cardholder Name','2-26'),
	'9F61' : ('Cardholder ID number','1-40'),
	'9F62' : ('Cardholder ID type','1'),	
	'5A' : ('PAN','1-10'),
	'5F24' : ('Application Expiration Date','3'),
	'5F25' : ('Application Effective Date','3'),
	'5F34' : ('Application PAN Sequence Number','1'),
	'9F07' : ('Application Usage Control','2'),
	'8E' : ('CVM List',),
	'9F0D' : ('IAC-Default','5'),
	'9F0E' : ('IAC-Denial','5'),
	'9F0F' : ('IAC-Online','5'),
	'5F28' : ('Issuer Country Code','2'),
	'9F4A' : ('Static Data Authentication Tag List','1'),
	'8C' : ('CDOL1',),
	'8D' : ('CDOL2',),
	'5F30' : ('Service Code','2'),
	'9F08' : ('Application Version Number','2'),
	'9F49' : ('DDOL',),
	'9F42' : ('Application Currency Code','2'),
	'9F44' : ('Application Currency Exponent','1'),	
	'8F' : ('CA Index','1'),
	'90' : ('IPK Certificate',),
	'92' : ('IPK Remainder',),
	'9F32' : ('IPK Exponent','1|3'),
	'9F46' : ('ICCPK Certificate',),
	'9F47' : ('ICCPK Exponent','1|3'),
	'9F48' : ('ICCPK Remainder',),
#Internal Data
	'82' : ('AIP','2'),
	'94' : ('AFL',),
	'9F10' : ('Issuer Application Data',),
	'9F36' : ('Application Transaction Counter (ATC)','2'),
	'9F13' : ('Last Online ATC Register','2'),
	'9F4F' : ('Log Format',),
	'9F51' : ('Application Currency Code','2'),
	'9F52' : ('Application Default Action','4|6'),
	'9F53' : ('CTCIL','1'),
	'9F54' : ('CTTAL','6'),
	'9F56' : ('Issuer Authentication Indicator','1'),
	'9F57' : ('Issuer Country Code','2'),
	'9F58' : ('CTCL','1'),
	'9F59' : ('CTCUL','1'),
	'9F5C' : ('CTTAUL','6'),
#Jetco Proprietary Data
	'DF41' : ('JDOL1',),
	'DF42' : ('JDOL2',),	'DF20' : ('Card Account Number',),
	'DF21' : ('Bank Number',),
	'DF22' : ('Card Sequence Number',),
	'DF23' : ('Language Code Field',),
	'DF25' : ('Network Proprietary Field',),
	'DF26' : ('Bill Reference Number List',),
	'DF27' : ('Transferee Account Number List',),	
	'DF50' : ('Issuer Proprietary Field',),
	'DF70' : ('Contactless Card Type',),
	
}

uics_tag_desc_mappings = {
#Command Response Data-DGI
	'9104' : ('GPO Response Data for UICS',),
	'9207' : ('GPO Response Data for qUICS',),	
	'9200' : ('Issuer application data',),
	'9102' : ('SELECT Command Response for contact mode',),
	'9103' : ('SELECT Command Response for contactless mode',),
#Internal Data-DGI
	'0D01' : ('Card internal risk management Data',),
	'0E01' : ('Card internal risk management Data',),
#Key-DGI
	'8000' : ('DES keys',),
	'9000' : ('DES Key Check Values',),
	'8010' : ('PIN block',),
	'9010' : ('PIN Related Data(PTC/PTL)',),
	'8201' : ('ICC Key CRT constant q-1 mod p',),
	'8202' : ('ICC Key CRT constant d mod (q – 1)',),
	'8203' : ('ICC Key CRT constant d mod (p – 1)',),
	'8204' : ('ICC Key CRT constant prime factor q',),
	'8205' : ('ICC Key CRT constant prime factor p',),
#Template Data
	'70' : ('Record Template',),
	'61' : ('Application Template',),
	'A5' : ('FCI Proprietary Template',),
	'BF0C' : ('FCI Issuer Discretionary Data',),	
#FCI Data
	'4F' : ('AID','5-16'),
	'50' : ('Application Label','1-16'),
	'87' : ('Application Priority Indicator','1'),
	'5F2D' : ('Language Preference','2-8'),
	'9F38' : ('PDOL',),
	'9F11' : ('Issuer Code Table Index','1'),
	'9F12' : ('Application Preferred Name','1-16'),
	'9F4D' : ('Log Entry','2'),
	'DF4D' : ('E-cash circular log entry','2'),
	'DF61' : ('Card Additional Function Indicator','1'),
#Record Data
	'57' : ('Track 2 Equivalent Data','1-19'),
	'9F1F' : ('Track 1 Discretionary Data',),
	'5F20' : ('Cardholder Name','2-26'),
	'9F61' : ('Cardholder ID number','1-40'),
	'9F62' : ('Cardholder ID type','1'),	
	'5A' : ('PAN','1-10'),
	'5F24' : ('Application Expiration Date','3'),
	'5F25' : ('Application Effective Date','3'),
	'5F34' : ('Application PAN Sequence Number','1'),
	'9F07' : ('Application Usage Control','2'),
	'8E' : ('CVM List',),
	'9F0D' : ('IAC-Default','5'),
	'9F0E' : ('IAC-Denial','5'),
	'9F0F' : ('IAC-Online','5'),
	'5F28' : ('Issuer Country Code','2'),
	'9F4A' : ('Static Data Authentication Tag List','1'),
	'8C' : ('CDOL1',),
	'8D' : ('CDOL2',),
	'5F30' : ('Service Code','2'),
	'9F08' : ('Application Version Number','2'),
	'9F49' : ('DDOL',),
	'9F42' : ('Application Currency Code','2'),
	'9F44' : ('Application Currency Exponent','1'),	
	'8F' : ('CA Index','1'),
	'90' : ('IPK Certificate',),
	'92' : ('IPK Remainder',),
	'9F32' : ('IPK Exponent','1|3'),
	'9F46' : ('ICCPK Certificate',),
	'9F47' : ('ICCPK Exponent','1|3'),
	'9F48' : ('ICCPK Remainder',),
	'9F69' : ('Card authentication related data','16'),
	'9F4B' : ('Signed Dynamic Application Data',),	
	'9F24' : ('PAR','29'),
	'9F74' : ('E-Cash Issuer Authorization Code','6'),
	'9F63' : ('Product Information','16'),
#Internal Data
	'82' : ('AIP','2'),
	'94' : ('AFL',),
	'9F10' : ('Issuer Application Data',),
	'9F36' : ('Application Transaction Counter (ATC)','2'),
	'9F13' : ('Last Online ATC Register','2'),
	'9F4F' : ('Log Format',),
	'9F51' : ('Application Currency Code','2'),
	'9F52' : ('Application Default Action','4|6'),
	'9F53' : ('CTCIL','1'),
	'9F54' : ('CTTAL','6'),
	'9F56' : ('Issuer Authentication Indicator','1'),
	'9F57' : ('Issuer Country Code','2'),
	'9F58' : ('CTCL','1'),
	'9F59' : ('CTCUL','1'),
	'9F5C' : ('CTTAUL','6'),
	'9F5D' : ('Available Offline Spending Amount','1'),
	'9F68' : ('Card Additional Processes','4'),
	'9F6B' : ('CVM Limit','6'),
	'9F6C' : ('Card Transaction Qualifier','2'),
	'9F6D' : ('E-Cash Reset Threshold','6'),
	'9F72' : ('CTCICL','1'),
	'9F73' : ('Currency Conversion Parameters','2'),
	'9F75' : ('CTTA Limit(Dual Currency)','6'),
	'9F76' : ('Application Currency Code(Dual Currency)','2'),
	'9F77' : ('E-Cash Balance Upper Limit','6'),
	'9F78' : ('Transaction Amount Limit','6'),
	'9F79' : ('E-Cash Balance','6'),
	'DF4F' : ('Load log format',),
	'DF62' : ('Fee deduction by segment limit','6'),
	'DF63' : ('Fee deducted by segment','6'),
	'DF71' : ('E-cash application currency code(Second currency)','2'),
	'DF76' : ('E-Cash Reset Threshold(Second currency)','6'),
	'DF77' : ('E-Cash Balance Upper Limit(Second currency)','6'),
	'DF78' : ('Transaction Amount Limit(Second currency)','6'),
	'DF79' : ('E-Cash Balance(Second currency)','6'),
}

pse_tag_desc_mappings = {
#DGI
	'9102' : ('SELECT Command Response of PSE',),
	'0101' : ('SFI 1 Record 1 of PSE',),
	'0102' : ('SFI 1 Record 2 of PSE',),
	'0103' : ('SFI 1 Record 3 of PSE',),
#Template Data
	'70' : ('Record Template',),
	'61' : ('Application Template',),
	'A5' : ('FCI Proprietary Template',),
	'BF0C' : ('FCI Issuer Discretionary Data',),	
#FCI Data
	'4F' : ('AID','5-16'),
	'50' : ('Application Label','1-16'),
	'87' : ('Application Priority Indicator','1'),
	'9F11' : ('Issuer Code Table Index','1'),
	'5F2D':('preference language','2|4'),
	'9F12' : ('Application Preferred Name','1-16'),
	'88' : ('SFI','1'),
}
ppse_tag_desc_mappings = {
#DGI
	'9102' : ('SELECT Command Response of PPSE',),
	'0101' : ('SFI 1 Record 1 of PPSE',),
	'0102' : ('SFI 1 Record 2 of PPSE',),
	'0103' : ('SFI 1 Record 3 of PPSE',),
#Template Data
	'70' : ('Record Template',),
	'61' : ('Application Template',),
	'A5' : ('FCI Proprietary Template',),
	'BF0C' : ('FCI Issuer Discretionary Data',),	
#FCI Data
	'4F' : ('AID','5-16'),
	'50' : ('Application Label','1-16'),
	'87' : ('Application Priority Indicator','1'),
	'9F11' : ('Issuer Code Table Index','1'),
	'9F12' : ('Application Preferred Name','1-16'),
	'5F2D':('preference language','2|4'),
	'88' : ('SFI','1'),
}