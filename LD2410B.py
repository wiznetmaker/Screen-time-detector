import busio
import board
import time
import binascii
import gc

#Standard Format from UART

# Command format
Command_head = b"\xFD\xFC\xFB\xFA"
Command_end = b"\x04\x03\x02\x01"
Command_mode_on = b"\xFF\x00\x01\x00"
Command_mode_off = b"\xFE\x00"
Parameters = b"\x61\x00"
Parameters_head = b"\xaa"
Factory_reset = b"\xA2\x00"
Reset = b"\xA3\x00"
check_distance_unit = b"\xAB\x00"
distance_unit = b"\xAA\x00"
sensitivity = b"\x64\x00"

# Output format
Out_head = b"\xf4\xf3\xf2\xf1"
Out_end = b"\xf8\xf7\xf6\xf5"
Out_data_head = b"\xaa"
Out_data_end = b"\x55"

class LD2410B:
    
    # Class Global Variables
    
    """
    Create a class to handle data from LD2410B sensor module
    

    :param: PIN TX_pin: Define RX PIN
            PIN RX_pin: Define TX PIN

    """
    
    def __init__ (self,Tx_pin: pin, Rx_pin: pin) -> None:
        self.uart = busio.UART(Tx_pin,Rx_pin, baudrate = 256000)
        #Variables:
        self.move_dist = None
        self.move_sen = None
        self.stable_dist = None
        self.stable_sen = None
        self.M_dist = None
        self.target = None
        self.W_type = None
        self.cmd_check = 0
    
    """
    Internal Function - Shifting data for data length in a correct format for command mode 
    

    :param: int cmd_size: the length for this command
    
    :return: bytes: 2 bytes length size

    """
    def _shifting(self,cmd_size = int) -> bytes:
        temp = cmd_size << 8 
        return temp.to_bytes(2,'big')
    
    """
    Internal Function - Check the command format is it correct
    

    :param: str mode : checking your current operation mode (data / command)
            str response : the full command from the module
    
    """    
    
    def _check_head_tail(self,mode, response) -> None:
        if mode is "data":
            head = Out_head
            tail = Out_end
            output = "Output"
        elif mode is "command":
            head = Command_head
            tail = Command_end
            output = "Command"
        else:
            raise ValueError ("Wrong head tail mode Input")
        
        if response[0:4] != head:
            raise ValueError ("Wrong {} Header".format(output))
        elif response[-4:] != tail:
            raise ValueError ("Wrong {} End".format(output))
        elif response[5]*256 + response[4] != len(response) - len(Out_head) - len(Out_end) - 2:
            raise ValueError ("Missing {} data".format(output))

    """
    Check / Set your command mode status
    
    Check :
    :return: int: 1 = ON / 0 = OFF
    
    Set :
    
    :param: int value: Values to set the mode. ( 1 = ON / 0 = OFF)
    
    """       
    
    @property
    def cmd_mode(self):
        return self.cmd_check
    
    @cmd_mode.setter
    def cmd_mode(self, value):
        if value == 1:
            data = Command_head + self._shifting(4) +Command_mode_on + Command_end
        elif value == 0:
            data = Command_head + self._shifting(2) +Command_mode_off + Command_end
        
        result =self._send_command(data)
        
        if result[0] == Command_mode_on[0]:
            print("Command Mode ON")
            self.cmd_check = 1
        elif result[0] == Command_mode_off[0]:
            print("Command Mode OFF")
            self.cmd_check = 0
    
    
    """
    Show all the setting parameters
    Included:
    1) Maximum Detection Range
    2) Maximum Detection Movement Range
    3) Maximum Detection Stable Range
    4) Detection Movement Sensitivity
    5) Detection Stable Sensitivity
    6) Waiting Time
    
    :return: str: the whole string for all parameters

    """
    @property
    def Parameters(self):
        data = Command_head + self._shifting(2) + Parameters + Command_end
        result =self._send_command(data)
        if result[4] != int.from_bytes(Parameters_head,'big'):
            raise ValueError("Command Word Response Error")
        
        string =("Maximum Detection Range: {}\n".format(result[5]) +
                "Maxiumum Detection Movement Range: {}\n".format(result[6]) +
                "Maxiumum Detection Stable Range: {}\n".format(result[7]))
        for i in range(8):
            temp = "Detection Movement Sensitivity {}: {}\n".format(i,result[8+i])
            string += temp
            temp = "Detection Stable Sensitivity {}: {}\n".format(i,result[17+i])
            string += temp
        
        string += "Waiting Time: {}".format(result[-1]*256 + result[-2])
        return string
    
    
    """
    Check and Set the module's Distance Unit: (0.2m / 0.75m)
    This module has two distance unit. 0.2m and 0.75m
    
    This module has set into different distance unit (Unit 0 - Unit 8).
    This function is to determine the distance between each distance units 

    Check:
    :return: str: show the current distance unit
    
    Set:
    :param: str value: set 0.2m or 0.75m

    """    
    @property
    def distance_unit(self):
        data = Command_head + self._shifting(2) + check_distance_unit + Command_end
        result =self._send_command(data)
        
        if result[-1] == 0:
            if result[-2] == 1:
                string = "0.2m Distance per Unit"
            elif result[-2] == 0:
                string = "0.75m Distance per Unit"
            else:
                raise ValueError ("Wrong distance Value 1")
        else:
            raise ValueError ("Wrong distance Value 2")
        
        return string
    
    @distance_unit.setter
    def distance_unit(self,value):
        if value == "0.2m":
            dist = self._shifting(1)
        elif value == "0.75m":
            dist = self._shifting(0)
        else:
            raise ValueError ("Please choose within 0.75m and 0.2m")
            
        data = Command_head + self._shifting(4) + distance_unit + dist + Command_end
        result =self._send_command(data)
        
        print("Module has set to {} distance unit".format(value))
        
    """
    Set your sensor sensitivity for each distance unit
    
    :param: int unit_sen: The distance unit value (0 - 8 / all)
            int move_sen: The sensitivity levels for movement sensors (0 - 10)
            int stable_sen: The sensitivity levels for stable sensors (0 - 10)
        
    """       
    def set_sensitivity(self,unit_sen: str, move_sen: int, stable_sen: int):
        padding = b"\x00\x00"
        move = b"\x01\x00"
        stable = b"\x02\x00"
        try:
            unit = self._shifting(int(unit_sen))
            
        except ValueError as error:
            if unit_sen is "all":
                unit = b"\xFF\xFF"
            else:
                raise ValueError ("Wrong sensitivity Input")
            
        except Exception as error:
            raise error
        
        data = Command_head + self._shifting(20) + sensitivity + padding + unit + padding
        data = data + move + self._shifting(move_sen) + padding
        data = data + stable + self._shifting(stable_sen) + padding + Command_end
        
        result =self._send_command(data)
        
        print ("Sensitivity has been Set!")
        
        
    """
    Factory Reset the module.
    It changes all the settings to default
    The settings will be activate after the modules has been reset    
    """               
    def factory_reset(self):
        data = Command_head + self._shifting(2) + Factory_reset + Command_end
        result =self._send_command(data)
        
        print("Module has reset to default setting! Please reset the module")
   
    """
    Reset the module.
    The module will reset itself 
    """             
    def reset(self):
        data = Command_head + self._shifting(2) + Reset + Command_end
        result =self._send_command(data)
        
        time.sleep(3)
        
        print("Module has reset!")
    
    """
    Internal Function - send the all the commands and receive feedbacks confirmation from the module
    

    :param: int cmd: the command set for each command
    
    :return: bytes: responsed command (head and tail removed)

    """        
    def _send_command (self,cmd: str, timeout: int = 5) -> None:
        #print(cmd)
        self.uart.write(cmd)
        
        self.uart.reset_input_buffer()
        gc.collect()
        stamp = time.monotonic()
        response = b""
        while (time.monotonic() - stamp) < timeout:
            if self.uart.in_waiting:
                response += self.uart.read(1)
                if Command_head in response and response[-4:] == Command_end:
                    break
        #print(response)
        #print(type(response))
        
        self._check_head_tail("command",response)
        if response[6] + response[7] != cmd[6] + cmd[7] + 1:
            raise ValueError("Command Word Response Error")
        elif response[8] + response[9] != 0:
            raise ValueError("Command Fail")
        
        return response[6:-4]
    """
    Collect data from sensor module
    Module will automatic send out result through UART.
    This function will automatically collect all those data to useful information

    :param: int timeout: Waiting time from UART. Default: 5 seconds 
    
    :return: int move_dist: Movement Object Distance - in cm
             int move_sen: Movement Object Sensitivty (0 -100)
             int stable_dist: Stable Object Distance - in cm
             int stable_sen: Stable Object Sensitivty (0 -100)
             int M_dist: Measuring distance - in cm

    """     

    def collect_data (self, timeout: int = 5) -> None:
        self.uart.reset_input_buffer()
        gc.collect()
        stamp = time.monotonic()
        response = b""
        while (time.monotonic() - stamp) < timeout:
            if self.uart.in_waiting:
                response += self.uart.read(1)
                if Out_head in response and response[-4:] == Out_end:
                    break
        #print(response)
        
        self._check_head_tail("data",response)
        if response[7] != int.from_bytes(Out_data_head,'big'):
            raise ValueError ("Wrong Output data Header")
        elif response[-6] != int.from_bytes(Out_data_end,'big'):
            raise ValueError ("Wrong Output data End")
        elif response[-5] != 0:
            raise ValueError ("Wrong checking point")
        
        #Checking operation Mode
        if response[6] == 2:
            self.W_type = "Basic Mode"
        elif response[6] == 1:
            self.W_type = "Engineering Mode"
        else:
            raise ValueError ("Wrong Working mode Data")
        
        #Checking target:
        if response[8] == 0:
            self.target = "No target"
        elif response[8] == 1:
            self.target = "Moving target"
        elif response[8] == 2:
            self.target = "Stable target"        
        elif response[8] == 3:
            self.target = "Both target"            
        else:
            raise ValueError ("Wrong Rarget Value")
        
        #Convert all the data
        self.move_dist = response[10]*256 + response[9]
        self.move_sen = response[11]
        self.stable_dist = response[13]*256 + response[12]
        self.stable_sen = response[14]
        self.M_dist = response[16]*256 + response[15]