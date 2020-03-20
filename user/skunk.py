#!/usr/bin/env python3
import fcntl
import struct
import ctypes

from ioctl_opt import IOWR, IOW

import skunk_pb2

class Skunk(object):
    def __init__(self):
        self.device_name = "/dev/skunk"
        self.func_call_ioctl_num = IOWR(0xEE, 0 ,ctypes.c_char_p)
        self.mock_create_ioctl_num = IOW(0xEE, 1 ,ctypes.c_char_p)

    def call_function(self, fname, num_args, fret, arg1, type1, arg2=None, type2=None, arg3=None, type3=None, arg4=None, type4=None):
        func_call = skunk_pb2.FunctionCall()
        func_call.returnType = fret
        func_call.numberOfArguments = num_args
        func_call.name = fname
        self._assign_arg(func_call.arg1, type1, arg1)
        
        if arg2 is not None and type2 is not None:
            self._assign_arg(func_call.arg2, type2, arg2)

        if arg3 is not None and type3 is not None:
            self._assign_arg(func_call.arg3, type3, arg3)

        if arg4 is not None and type4 is not None:
            self._assign_arg(func_call.arg4, type4, arg4)

        func_with_one_arg_binary = self._binary_length_and_value(func_call.SerializeToString(), func_call.ByteSize())
        
        with open(self.device_name, 'r') as skunk_device:
            call_result = fcntl.ioctl(skunk_device, self.func_call_ioctl_num, func_with_one_arg_binary)

        length_of_size_field = struct.calcsize('I')
        return_length, = struct.unpack('I', call_result[:length_of_size_field])

        return_value = skunk_pb2.ReturnValue()
        return_value.ParseFromString(call_result[length_of_size_field:length_of_size_field + return_length])

        if (return_value.status != skunk_pb2.ReturnValue.Success):
            error_string = skunk_pb2.ReturnValue.CallStatus.keys()[return_value.status]
            raise RuntimeError(f"Unable to perform function call due to error {error_string}")

        return return_value

    def create_mock(self):
        with open(self.device_name, 'r') as skunk_device:
            fcntl.ioctl(skunk_device, self.mock_create_ioctl_num, b"")

    @staticmethod
    def _assign_arg(protobuf_arg, arg_type, arg_value):
        protobuf_arg.type = arg_type
        if arg_type == skunk_pb2.Argument.string:
            protobuf_arg.arg_string = arg_value
        elif arg_type == skunk_pb2.Argument.eight_byte:
            protobuf_arg.arg_eight_byte = arg_value
        elif arg_type == skunk_pb2.Argument.four_byte:
            protobuf_arg.arg_four_byte = arg_value
        else:
            raise ValueError("Unsupported argument type")
    
    @staticmethod
    def _binary_length_and_value(buffer, buffer_length):
        return struct.pack('I', buffer_length) + buffer