# -*- coding: utf-8 -*-
#
# Copyright 2015 error.d
# by error.d@gmail.com
# 2015-04-23
#

#
# AML -- Assembly&Map Language
#

import copy
import logging


class AMLStateMachine(object):
    """
    core logic:
      result = template + data

    core state machine transform:
      struct_check -> basestring -> assignment -> stop
                   -> number -> assignment -> stop
                   -> bool -> assignment -> stop
                   -> list -> move_list -> struct_check -| -> stop
                                  ^                      |
                                  |-----------------------
                           -> type_list -> recursive amlsm
                   -> dict -> move_dict -> struct_check -| -> stop
                                  ^                      |
                                  |-----------------------
                           -> type_dict -> recursive amlsm
                   -> amlmap -> [location] -> action -> for
                                                     -> if_key
                                                     -> location
                                                     -> root_location

    state stack:
      1. dict and list on python function call stack
    """

    ### state start ###
    # base state
    STATE_stop = 0
    STATE_init = 1
    STATE_init_map = 2
    STATE_init_list = 3
    STATE_move_dict = 4 # move to dict node
    STATE_move_list = 5 # move to list node
    # struct state
    STATE_struct_check = 10
    STATE_struct_type_string = 11
    STATE_struct_type_number = 12
    STATE_struct_type_bool = 13
    STATE_struct_type_list = 14
    STATE_struct_type_dict = 15
    STATE_struct_type_amlmap = 16
    # map
    STATE_map_key = 20
    STATE_map_index = 21
    # action state
    STATE_amlmap_action_location = 30
    STATE_amlmap_action_root_location = 31
    STATE_amlmap_action_if_key = 33
    STATE_amlmap_action_for_list = 32
    # No support state
    STATE_struct_type_func = 50

    ### state end ###

    # struct type
    STRUCT_nop  = 0
    STRUCT_dict = 1
    STRUCT_list = 2


    AMAP_CMD = 'amap'

    @classmethod
    def global_initialize(cls):
        cls.MAP_order_cache = dict()

    def __init__(self, debug, level=0):
        self._debug = debug
        self._level = level + 1
        self._off = True
        self._struct_type = AMLStateMachine.STRUCT_nop
        self._last_state = AMLStateMachine.STATE_init

        # data
        self._cur_state = AMLStateMachine.STATE_init
        self._template = None
        self._cur_location = None
        self._data = None
        self._global_cur_data = None
        self._cur_data = None
        self._result = None
        self._amap = None
        self._action = None

        # struct dict
        self._dict_stack = []
        self._dict_key = None

        # struct list
        self._list_size = 0
        self._list_idx = 0

        self._temp = None

        # init state machine
        self._init_state_machine()

        # debug
        self._state_transform_list = []

    def _clear(self):
        self._template = None
        self._cur_location = None
        self._data = None
        self._cur_data = None
        self._result = None

    def __debug(self, msg, *args):
        if self._debug:
            logging.debug('[AMLStateMachine] %s %s' % (('-' * 2+'>') * self._level,
                                                       msg),
                          *args)

    def __state_run(self, state):
        if self._debug:
            self._state_transform_list.append('%s:%s' % (self._level, state))
        self.__debug('action [%s] run', state)

    def _init_state_machine(self):
        self._state_action_map = {
            AMLStateMachine.STATE_init: self.__action__state_init,
            AMLStateMachine.STATE_stop: self.__action__state_stop,
            AMLStateMachine.STATE_init_map: self.__action__state_init_map,
            AMLStateMachine.STATE_init_list: self.__action__state_init_list,
            AMLStateMachine.STATE_move_dict: self.__action__state_move_dict,
            AMLStateMachine.STATE_move_list: self.__action__state_move_list,
            AMLStateMachine.STATE_struct_check: self.__action__state_struct_check,
            AMLStateMachine.STATE_struct_type_string: self.__action__state_type_string,
            AMLStateMachine.STATE_struct_type_number: self.__action__state_type_number,
            AMLStateMachine.STATE_struct_type_bool: self.__action__state_type_bool,
            AMLStateMachine.STATE_struct_type_dict: self.__action__state_type_dict,
            AMLStateMachine.STATE_struct_type_list: self.__action__state_type_list,
            AMLStateMachine.STATE_struct_type_amlmap: self.__action__state_type_amlmap,
            AMLStateMachine.STATE_map_key: self.__action__map_key,
            AMLStateMachine.STATE_map_index: self.__action__map_index,
            # action state
            AMLStateMachine.STATE_amlmap_action_location: \
            self.__action__state_amlmap_action_location,
            AMLStateMachine.STATE_amlmap_action_root_location: \
            self.__action__state_amlmap_action_root_location,
            AMLStateMachine.STATE_amlmap_action_if_key: \
            self.__action__state_amlmap_action_if_key,
            AMLStateMachine.STATE_amlmap_action_for_list: \
            self.__action__state_amlmap_action_for_list
            }

    def set_struct_type(self, struct_type):
        self._struct_type = struct_type

    def set_cur_state(self, state):
        self._cur_state = state

    def set_last_state(self, state):
        self._last_state = state

    def set_state_action(self, state, action):
        self._state_action_map[state] = action

    def state_action(self):
        action = self._state_action_map.get(self._cur_state, None)
        assert action, "State: %s no action, last_state: %s !!!" % (
            self._cur_state, self._last_state)
        return action

    def _trans_state(self, cur_state, last_state=None, struct_type=None):
        if last_state:
            self.set_last_state(last_state)
        if struct_type:
            self.set_struct_type(struct_type)
        self.set_cur_state(cur_state)

    def _assignment(self):
        if self._struct_type is AMLStateMachine.STRUCT_dict:
            self._result[self._dict_key] = self._temp
        elif self._struct_type is AMLStateMachine.STRUCT_list:
            self._result.append(self._temp)

    def _assignment_or_recursive(self, template, cur_data):
        if isinstance(template, (dict, list)):
            self._recursive_asm(template=template, cur_data=cur_data)
        else:
            self._temp = template
            self._assignment()
            self._trans_state(self._last_state)

    def _recursive_asm(self, state_msg=None, template=None, cur_data=None):
        if state_msg:
            self.__state_run(state_msg)
        cur_location = template if template else self._cur_location
        global_cur_data = cur_data if cur_data else self._global_cur_data
        asm = AMLStateMachine(debug=self._debug, level=self._level)
        self._temp = asm.starting(cur_location, self._data,
                                  global_cur_data=global_cur_data)
        self._state_transform_list += asm.get_state_transform_list()
        self._assignment()
        self._trans_state(self._last_state)

    ### data

    def _data_location(self, locations, is_global=True, root_location=False):
        if root_location:
            cur_data = self._data
        else:
            cur_data = self._global_cur_data
        locations = [locations] if isinstance(locations, basestring) else locations

        for loc in locations:
            # string is key of dict
            # number is index of list
            cur_data = cur_data[loc]
            self.__debug("%s move location: %s", 'root_location' if root_location \
                         else 'location', loc)

        if is_global:
            self._global_cur_data = cur_data
        else:
            self._cur_data = cur_data

    ### action

    def __action__state_init(self):
        self.__state_run('init')
        self.set_last_state(AMLStateMachine.STATE_init)
        self._trans_state(AMLStateMachine.STATE_struct_check)

    def __action__state_stop(self):
        self.__state_run('stop')
        self._off = True

    def __action__state_init_map(self):
        self.__state_run('init_map')
        self._result = dict()

        # use cache
        cache_key = id(self._cur_location)
        dict_stack = AMLStateMachine.MAP_order_cache.get(cache_key, [])
        if dict_stack == []:
            # run ampmap order
            max_idx = AMLMap.RUN_IDX + 1
            sort_list = map(lambda x: (x[1].run_idx, x[0]) if \
                            isinstance(x[1], AMLMap) else (max_idx, x[0]),
                            self._cur_location.items())
            sort_list.sort(key=lambda x: x[0], reverse=True)
            self.__debug('run_idx order: %s', sort_list)
            dict_stack = [item[1] for item in sort_list]

            # amap_cmd to top
            amap_cmd = AMLStateMachine.AMAP_CMD
            if amap_cmd in dict_stack:
                self.__debug('amap_cmd top')
                dict_stack.remove(amap_cmd)
                dict_stack.append(amap_cmd)
            # into cache
            AMLStateMachine.MAP_order_cache[cache_key] = dict_stack

        self._dict_stack = copy.copy(dict_stack)
        self._trans_state(AMLStateMachine.STATE_move_dict)

    def __action__state_init_list(self):
        self.__state_run('init_list')
        self._result = list()
        self._list_size = len(self._cur_location)
        self._list_idx = 0
        self._trans_state(AMLStateMachine.STATE_move_list)

    def __action__state_move_dict(self):
        self.__state_run('move_tn_dict')
        self.__debug('dict keys: %s', self._dict_stack)

        # stop
        if len(self._dict_stack) == 0:
            self._trans_state(AMLStateMachine.STATE_stop)
            return

        key = self._dict_stack.pop()
        self._cur_location = self._template[key]
        self._dict_key = key
        self._trans_state(AMLStateMachine.STATE_struct_check,
                          last_state=AMLStateMachine.STATE_move_dict,
                          struct_type=AMLStateMachine.STRUCT_dict)

    def __action__state_move_list(self):
        self.__state_run('move_tn_list')
        self._list_idx += 1
        self.__debug('list size:%s idx:%s', self._list_size, self._list_idx)

        # stop
        if self._list_idx > self._list_size:
            self._trans_state(AMLStateMachine.STATE_stop)
            return

        # index base on 1
        self._cur_location = self._template[self._list_idx-1]
        self._trans_state(AMLStateMachine.STATE_struct_check,
                          last_state=AMLStateMachine.STATE_move_list,
                          struct_type=AMLStateMachine.STRUCT_list)

    def __action__state_struct_check(self):
        self.__state_run('struct_check')
        node = self._cur_location
        if isinstance(node, basestring):
            self.set_cur_state(AMLStateMachine.STATE_struct_type_string)
        elif isinstance(node, bool):
            self.set_cur_state(AMLStateMachine.STATE_struct_type_bool)
        elif isinstance(node, (int, long, float)):
            self.set_cur_state(AMLStateMachine.STATE_struct_type_number)
        elif isinstance(node, dict):
            if self._last_state is AMLStateMachine.STATE_init:
                self.set_cur_state(AMLStateMachine.STATE_init_map)
            else:
                self.set_cur_state(AMLStateMachine.STATE_struct_type_dict)
        elif isinstance(node, list):
            if self._last_state is AMLStateMachine.STATE_init:
                self.set_cur_state(AMLStateMachine.STATE_init_list)
            else:
                self.set_cur_state(AMLStateMachine.STATE_struct_type_list)
        elif isinstance(node, AMLMap):
            self.set_cur_state(AMLStateMachine.STATE_struct_type_amlmap)
        else:
            assert 0, 'Unknow node: %s' % node

    def __action__state_type_basic(self):
        self._temp = self._cur_location
        self._assignment()
        self._trans_state(self._last_state)

    def __action__state_type_string(self):
        self.__state_run('type_string')
        self.__action__state_type_basic()

    def __action__state_type_number(self):
        self.__state_run('type_number')
        self.__action__state_type_basic()

    def __action__state_type_bool(self):
        self.__state_run('type_bool')
        self.__action__state_type_basic()

    def __action__state_type_dict(self):
        self._recursive_asm(state_msg='type_dict')

    def __action__state_type_list(self):
        self._recursive_asm(state_msg='type_list')

    def __action__map_key(self):
        data_key = self._amap.key
        self._temp = None

        if not isinstance(self._cur_data, dict):
            logging.error("map_key '%s' data no dict data:%s",
                          self._dict_key, self._cur_data)
        elif data_key not in self._cur_data:
            logging.error("map_key '%s' from '%s' failed data:%s",
                          self._dict_key, data_key, self._cur_data)
        else:
            temp = self._cur_data[data_key]
            self._temp = self._amap.type(temp) if self._amap.type else temp

        self._assignment()
        self._trans_state(self._last_state)

    def __action__map_index(self):
        index = self._amap.index
        self._temp = None

        if not isinstance(self._cur_data, list):
            logging.error("map_index '%s' data no list data:%s",
                          self._list_idx, self._cur_data)
        elif index >= len(self._cur_data):
            logging.error("map_index '%s' from '%s' failed data:%s",
                          self._list_idx, index, self._cur_data)
        else:
            temp = self._cur_data[index]
            self._temp = self._amap.type(temp) if self._amap.type else temp

        self._assignment()
        self._trans_state(self._last_state)

    def __action__state_type_amlmap(self):
        self.__state_run('type_amlmap')
        amap = self._cur_location
        # reset cur_data, clear a amap local cur_data setting
        self._cur_data = self._global_cur_data
        if amap.location:
            self._data_location(amap.location, is_global=False)
        if amap.root_location:
            self._data_location(amap.root_location, is_global=False,
                                root_location=True)

        self._amap = amap
        self._action = amap.action
        if amap.action:
            self._trans_state(amap.action.action_state())
        elif amap.key:
            self._trans_state(AMLStateMachine.STATE_map_key)
        elif amap.index:
            self._trans_state(AMLStateMachine.STATE_map_index)
        else:
            logging.error('Unknow Amap %s !!!', amap)
            self._trans_state(AMLStateMachine.STATE_stop)

    def __action__state_amlmap_action_location(self):
        self.__state_run('amlmap_action_location')
        action = self._action
        locations = action.argument_list[0]
        assert locations, "action location needs has argument 'locations'!!!"
        self._data_location(locations)
        self._trans_state(self._last_state)

    def __action__state_amlmap_action_root_location(self):
        self.__state_run('amlmap_action_root_location')
        action = self._action
        locations = action.argument_list[0]
        assert locations, "action root_location needs has argument 'locations'!!!"
        self._data_location(locations, root_location=True)
        self._trans_state(self._last_state)

    def _create_action(self, action_class):
        action_obj = action_class(self._action, self._cur_location, self._cur_data)
        assert action_obj.parse(), action_obj.error_message()        
        assert action_obj.validity_check(), action_obj.error_message()
        return action_obj

    def __action__state_amlmap_action_if_key(self):
        self.__state_run('amlmap_action_if_key')
        action_ifkey = self._create_action(Action_Ifkey)
        template = action_ifkey.exec_action()
        if template is not None:
            self._assignment_or_recursive(template, self._cur_data)
        else:
            self._trans_state(self._last_state)

    def __action__state_amlmap_action_for_list(self):
        self.__state_run('amlmap_action_for_list')
        action_forlist = self._create_action(Action_ForList)
        def for_iter_callback(template, data):
            self._recursive_asm(template=template, cur_data=data)
            return Action_ForList.ITER_state_continue

        action_forlist.exec_action(for_iter_callback)
        self._trans_state(self._last_state)

    # user interface

    def get_state_transform_list(self):
        return self._state_transform_list

    def starting(self, template, data, global_cur_data=None):
        # init data
        self._template = template
        self._data = data
        self._global_cur_data = global_cur_data if global_cur_data else data
        self._cur_location = self._template
        self._off = False

        # state machine starting!!!!
        self.__debug('starting!!')
        while not self._off:
            self.state_action()()
        self.__debug('stop!!')

        result = self._result
        self._clear()
        return result

class AMLMap(object):
    RUN_IDX = 0
    def __init__(self, key=None, index=None, action=None,
                 type=None, location=None, root_location=None):
        """
        key: map by dict key
        index: map by list index
        action: xx
        type: xx
        location: [string, int], string is dict key, int is list index
        """
        AMLMap.RUN_IDX += 1
        self.run_idx = AMLMap.RUN_IDX
        self.key = key
        self.index = index
        self.action = action
        self.type = type
        self.location = location
        self.root_location = root_location
        assert not (location and root_location), \
               'location and root_location two choose one'

    def __str__(self):
        argument_tuple = (id(self), self.run_idx, self.key, \
                          self.index, self.action, self.type, \
                          self.location, self.root_location)
        return "<AMLMap at 0x%x run_idx:%s key:%s " \
               "index:%s action:%s type:%s location:%s " \
               "root_location:%s >" % argument_tuple

    __repr__ = __str__

class AMLAction(object):
    action_map = {
        'root_location': AMLStateMachine.STATE_amlmap_action_root_location,
        'location': AMLStateMachine.STATE_amlmap_action_location,
        'if_key': AMLStateMachine.STATE_amlmap_action_if_key,
        'for_list': AMLStateMachine.STATE_amlmap_action_for_list
        }
    def __init__(self, action, *args, **kwargs):
        assert action in AMLAction.action_map, "Unknow action: '%s'" % action
        self.action_name = action
        self.argument_list = args
        self.argument_dict = kwargs

    def action_state(self):
        return AMLAction.action_map.get(self.action_name, None)

    def __str__(self):
        return "<AMLAction at 0x%x action:%s argument_list:%s argument_dict:%s>" % \
               (id(self), self.action_name, self.argument_list, self.argument_dict)

    __repr__ = __str__


class ActionBase(object):

    COMPARE_op_actons = {
        '==' : lambda v1, v2: v1 == v2,
        '>=' : lambda v1, v2: v1 >= v2,
        '>'  : lambda v1, v2: v1 > v2,
        '<=' : lambda v1, v2: v1 <= v2,
        '<'  : lambda v1, v2: v1 < v2,
        '!=' : lambda v1, v2: v1 != v2
        }

    CHECKPOINT_list = {}
    
    def __init__(self, action, template, data):
        assert hasattr(self, 'action_name'), 'Action class need action_name attr!!!'
        self._action = action
        self._template = template
        self._data = data
        self._error_messages = []
        self._validity_result = True
        self._load_checkpoint()
        self._validity_checkpoint_list = ActionBase.CHECKPOINT_list[self.action_name]

    def _load_checkpoint(self):
        if self.action_name in ActionBase.CHECKPOINT_list:
            return

        checkpoint_list = [] 
        ActionBase.CHECKPOINT_list[self.action_name] = checkpoint_list
        logging.debug('%s load checkpoint', self.action_name)
        symbol_list = dir(self)
        for symbol in symbol_list:
            if symbol.startswith('_checkpoint__'):
                logging.debug('-- load %s', symbol)
                checkpoint_list.append(symbol)

    def data(self):
        return self._data

    def template(self):
        return self._template

    def add_error_message(self, error_message):
        self._error_messages.append(error_message)

    def add_validity_checkpoint(self, checkpoint):
        self._validity_checkpoint_list.append(checkpoint)

    def error_message(self):
        for idx, msg in enumerate(self._error_messages):
            self._error_messages[idx] = '%s. %s' % (idx+1, msg)
        return '\n'.join(self._error_messages)

    def parse_failure(self):
        self._parse_state = False

    def parse(self):
        self._parse_state = True
        self._parse()
        return self._parse_state

    def _parse(self):
        pass

    def check_failure(self):
        self._validity_result = False

    def validity_check(self):
        for checkpoint_name in self._validity_checkpoint_list:
            getattr(self, checkpoint_name)()
            if not self._validity_result:
                return self._validity_result
        self._validity_check()
        return self._validity_result

    def _validity_check(self):
        pass

class Action_Ifkey(ActionBase):
    action_name = 'action_ifkey'

    def __init__(self, action, template, data):
        super(Action_Ifkey, self).__init__(action, template, data)

    def _parse(self):
        action = self._action
        if len(action.argument_list) != 3:
            self.add_error_message('parse faield, argument error, ' \
                                   'need has key, op, value. argument:%s' % \
                                   str(action.argument_list))
            self.parse_failure()
            return
        self._key = action.argument_list[0]
        self._op = action.argument_list[1]
        self._value = action.argument_list[2]
        self._block_template = action.argument_dict.get('block_template', None)
        self._else_template = action.argument_dict.get('else_template', None)

    def _checkpoint__1_exists(self):
        if not (self._key and self._op and self._value != None):
            self.add_error_message("key or op or value not exists, " \
                                   "key:'%s', op:'%s', value:'%s'" % (
                                   self._key, self._op, self._value)
                                   )
            self.check_failure()

        if not (self._block_template or self._else_template):
            self.add_error_message('block_template and else_template ' \
                                   'two choose one')
            self.check_failure()

    def _checkpoint__2_type(self):
        if self._key not in self.data():
            self.add_error_message('key: %s not in %s' % (self._key, self._data))
            self.check_failure()

        if self._op not in Action_Ifkey.COMPARE_op_actons.keys():
            self.add_error_message("if_key op '%s' not support, support %s" % \
                                   (self._op, Action_Ifkey.COMPARE_op_actons.keys()))
            self.check_failure()

    def exec_action(self):
        data_value = self.data()[self._key]
        if Action_Ifkey.COMPARE_op_actons[self._op](data_value, self._value):
            return self._block_template
        else:
            return self._else_template

class Action_ForList(ActionBase):
    action_name = 'action_forlist'

    ITER_state_continue = 0
    ITER_state_break = 1

    def __init__(self, action, template, data):
        super(Action_ForList, self).__init__(action, template, data)

    def _parse(self):
        action = self._action
        self._template = action.argument_dict.get('template', None)
        
        if len(action.argument_list) is not 0:
            self.add_error_message("No support 'for_list' type, argument: %s" % \
                                   str(action.argument_list))
            self.parse_failure()

    def _checkpoint__1_template(self):
        if not self._template:
            self.add_error_message("'for_list' need has argument 'template'")
            self.check_failure()

    def _checkpoint__2_data_is_list(self):
        if not isinstance(self.data(), list):
            self.add_error_message("'for_list' data need has list data:%s" % \
                                   str(self.data()))
            self.check_failure()

    def exec_action(self, iter_callback):
        for data_item in self.data():
            iter_state = iter_callback(self.template(), data_item)
            if iter_state is Action_ForList.ITER_state_break:
                break

class AML(object):
    def __init__(self, debug=False, level=0):
        self._debug = debug
        self._amlsm = AMLStateMachine(debug, level)
        AMLStateMachine.global_initialize()

    def _assembly_and_map(self, template, data):
        return self._amlsm.starting(template, data)

    def run(self, template, data):
        if isinstance(template, basestring):
            return template
        result = self._assembly_and_map(template, data)
        if self._debug:
            state_transform_list = self._amlsm.get_state_transform_list()
            logging.debug('state transform: %s',
                          ' -> '.join(map(lambda x: "[%s]" % x,
                                          state_transform_list)))
        return result
