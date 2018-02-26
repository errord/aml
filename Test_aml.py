#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# by error.d@gmail.com
# 2015-05-20
#

import sys
import logging
sys.path.insert(0, '../')


logging.getLogger().setLevel(logging.DEBUG)

from aml import AML, AMLMap as AMap, AMLAction as Action


def setUp():
    pass

def tearDown():
    pass

def Test_string():
    template = "abc"
    aml = AML(debug=True)
    r = aml.run(template, {})
    assert r == template, 'string failed template:%s result:%s' % (template, r)

def Test_dict():
    template = {
        'test': 'test11'
        }
    aml = AML(debug=True)
    r = aml.run(template, {})
    assert r == template, 'dict failed template:%s result:%s' % (template, r)

    template = {
        'test1': 'test11',
        'test': {
        'test2': 'test122',
        'test3': {
        'test4': '1111111111111'
        }
        },
        'test5': {
        'test6': {
        'test7': {
        }
        }
        },
        'test8': '88888'
        }

    aml = AML(debug=True)
    r = aml.run(template, {})
    assert r == template, 'dict failed template:%s result:%s' % (template, r)

def Test_list():
    template = ['llll',
                'iiii',
                'ssss',
                'tttt']
    
    aml = AML(debug=True)
    r = aml.run(template, {})
    assert r == template, 'list failed template:%s result:%s' % (template, r)

def Test_dict_and_list():
    template = {
        'test': 'test',
        'test_dict': {
        'TEST2': 'test2',
        'test_list': ['list1', 'list2', ['111', 222, '333']],
        'Bool': True,
        },
        }

    aml = AML(debug=True)
    r = aml.run(template, {})
    assert r == template, 'dict and list failed template:%s result:%s' % (template, r)

def Test_amp_key_and_location_and_dcit_amap_cmd():
    template = {
        "represent_type": "list",
        "represent_data": {
        "amap"                : AMap(action=Action('location', ['level'])),
        "title"               : AMap(location='level2', key='policyName', type=str),
        "ticket_description"  : AMap(key='remark', type=str),
        "price"               : AMap(key='tcPrice', type=int),
        "sell_status"         : 2,
        "pay_type"            : AMap(location='level3', key='pMode', type=int),
        "price_info"          : AMap(key='tcPrice', type=int)
        }
        }
    
    data = {
        'level': {
        'level2': {
        'policyName': 'aaaaaaaaaaaaaaaasssss',
        },
        'level3': {
        'pMode': 1,
        },
        'remark': 'bbbbbasdf',
        'tcPrice': 20,
        'tcPrice': 15
        }
        }

    check_result = {'represent_data':
                    {'pay_type': 1, 'title': 'aaaaaaaaaaaaaaaasssss',
                     'price': 15, 'sell_status': 2,
                     'ticket_description': 'bbbbbasdf', 'price_info': 15},
                    'represent_type': 'list'}

    aml = AML(debug=True)
    r = aml.run(template, data)

    assert r == check_result, 'amp_key_and_location_and_dcit_amap_cmd faield' \
           ' check_result: %s result: %s' % (check_result, r)


def Test_amp_list_and_location_and_list_amap_cmd_and_type():

    template = {
        "represent_type": "list",
        "represent_data": [
        AMap(action=Action('location', ['level'])),
        {
        "title"               : AMap(location='level2', key='policyName', type=str),
        'root_data'           : AMap(root_location=['ROOT_path', 't', 1, 'r2', 2],
                                     index=1, type=str),
        "ticket_description"  : AMap(key='remark', type=str),
        "price"               : AMap(key='tcPrice', type=str),
        "sell_status"         : 2,
        "pay_type"            : AMap(key='pMode', type=int),
        "price_info"          : AMap(key='tcPrice', type=int)
        },
        ]
        }
    
    data = {
        'ROOT_path': {
        't': [{},
              {'r2': [0, 2302, [1, 'rrrrooootttt']]}
              ],
        },
        'level': {
        'level2': {
        'policyName': 'aaaaaaaaaaaaaaaasssss',
        },
        'pMode': 1,
        'remark': 'bbbbbasdf',
        'tcPrice': 20,
        'tcPrice': 15
        }
        }

    check_result = {'represent_data':
                    [{'pay_type': 1,
                      'title': 'aaaaaaaaaaaaaaaasssss',
                      'price': '15',
                      'sell_status': 2,
                      'ticket_description': 'bbbbbasdf',
                      'price_info': 15,
                      'root_data': 'rrrrooootttt'
                      }
                     ],
                    'represent_type': 'list'}

    aml = AML(debug=True)
    r = aml.run(template, data)

    assert r == check_result, 'amp_list_and_location_and_list_amap_cmd faield' \
           ' check_result: %s result: %s' % (check_result, r)

def Test_if():
    
    template = {
        "represent_type": "list",
        "represent_data": [
        AMap(action=Action('location', ['level'])),
        {
        "title"               : AMap(location='level2', key='policyName', type=str),
        'root_data'           : AMap(root_location=['ROOT_path', 't', 1, 'r2', 2],
                                     index=1, type=str),
        "ticket_description"  : AMap(key='remark', type=str),
        "price"               : AMap(key='tcPrice', type=str),
        "sell_status"         : 2,
        "pay_type"            : AMap(key='pMode', type=str),
        "price_info"          : AMap(key='tcPrice', type=str),
        "card": AMap(root_location=['ROOT_path', 'n'],
                     action=Action('if_key', 'useCard', '==', u'1',
                                   block_template={"restriction": "",
                                                   "type": "fill",
                                                   "value": ""})),
        "if_else_1": AMap(action=Action('if_key', 'tcPrice', '>=', u'1',
                                        block_template={"1111": "",
                                                        "2222": "fill",
                                                        "3333": ""},
                                        else_template={"4444": "4444",
                                                       "5555": "aaaa",
                                                       "6666": 23434})),
        "if_else_2": AMap(action=Action('if_key', 'tcPrice', '<', u'1',
                                        block_template={"1111": "",
                                                        "2222": "fill",
                                                        "3333": ""},
                                        else_template={"4444": "4444",
                                                       "5555": "aaaa",
                                                       "6666": 23434})),
        "if_else_3": AMap(action=Action('if_key', 'tcPrice', '>', 1,
                                        block_template={"a1111": "",
                                                        "2222": "fill",
                                                        "3333": ""},
                                        else_template={"b4444": "4444",
                                                       "5555": "aaaa",
                                                       "6666": 23434})),
        },
        ]
    }

    data = {
        'ROOT_path': {
        't': [{},
              {'r2': [0, 2302, [1, 'rrrrooootttt']]}
              ],
        'n': {
        'useCard': u'1'
        }
        },
        'level': {
        'level2': {
        'policyName': 'aaaaaaaaaaaaaaaasssss',
        },
        'pMode': 1,
        'remark': 'bbbbbasdf',
        'tcPrice': 20,
        'tcPrice': 15
        }
        }

    check_result = {'represent_data': [
        {'card': {'restriction': '', 'type': 'fill', 'value': ''},
         'pay_type': '1', 'title': 'aaaaaaaaaaaaaaaasssss', 'price': '15',
         'if_else_3': {'3333': '', 'a1111': '', '2222': 'fill'}, 'sell_status': 2, 'ticket_description': 'bbbbbasdf', 'price_info': '15',
         'if_else_2': {'3333': '', '1111': '', '2222': 'fill'},
         'if_else_1': {'5555': 'aaaa', '6666': 23434, '4444': '4444'},
         'root_data': 'rrrrooootttt'}
        ],
        'represent_type': 'list'
        }

    aml = AML(debug=True)
    r = aml.run(template, data)

    assert r == check_result, 'if faield' \
           ' check_result: %s result: %s' % (check_result, r)
    

def Test_for():
    template = {
        "represent_type": "list",
        "represent_data": [
        AMap(location=['policy_list'], action=Action('for_list', template={
        "title"               : AMap(key='policyName', type=str),
        "ticket_description"  : AMap(key='remark', type=str),
        "price"               : AMap(key='tcPrice', type=str),
        "sell_status"         : 2,
        "pay_type"            : AMap(key='pMode', type=int),
        "price_info"          : AMap(key='tcPrice', type=str)}))
        ]
        }

    data = {
        'policy_list' : [
        {
        'policyName': 'aaaaaaaaaaaaaaaasssss',
        'pMode': 1,
        'remark': 'bbbbbasdf',
        'tcPrice': 20,
        'useCard': u'1'    
        },
        {
        'policyName': '22222222222222222222222',    
        'pMode': 1,
        'remark': 'bbbbbasdf',
        'tcPrice': 20,
        'useCard': u'0'    
        },
        {
        'policyName': '3333333333333333333333333',    
        'pMode': 1,
        'remark': 'bbbbbasdf',
        'tcPrice': 20,
        'useCard': u'1'    
        },
        {
        'policyName': '4444444444444444444444444',    
        'pMode': 1,
        'remark': 'bbbbbasdf',
                    'tcPrice': 20,
        'useCard': u'0'
        },    
        ]
        }


    check_result = {'represent_data': [{'pay_type': 1,
                                        'price': '20',
                                        'price_info': '20',
                                        'sell_status': 2,
                                        'ticket_description': 'bbbbbasdf',
                                        'title': 'aaaaaaaaaaaaaaaasssss'},
                                       {'pay_type': 1,
                                        'price': '20',
                                        'price_info': '20',
                                        'sell_status': 2,
                                        'ticket_description': 'bbbbbasdf',
                                        'title': '22222222222222222222222'},
                                       {'pay_type': 1,
                                        'price': '20',
                                        'price_info': '20',
                                        'sell_status': 2,
                                        'ticket_description': 'bbbbbasdf',
                                        'title': '3333333333333333333333333'},
                                       {'pay_type': 1,
                                        'price': '20',
                                        'price_info': '20',
                                        'sell_status': 2,
                                        'ticket_description': 'bbbbbasdf',
                                        'title': '4444444444444444444444444'}],
                    'represent_type': 'list'}
    
    aml = AML(debug=True)
    r = aml.run(template, data)

    assert r == check_result, 'if faield' \
           ' check_result: %s result: %s' % (check_result, r)
