import time
import board
import LD2410B

dist_sen = LD2410B.LD2410B(board.GP0,board.GP1)
#print (dist_sen.cmd_mode)
dist_sen.cmd_mode = 1
#print (dist_sen.cmd_mode)
#dist_sen.factory_reset()
#dist_sen.reset()
#print(dist_sen.Parameters)
#print(dist_sen.distance_unit)
#dist_sen.distance_unit = "0.2m"
#print(dist_sen.distance_unit)
#dist_sen.distance_unit = "0.75m"
#print(dist_sen.distance_unit)
dist_sen.set_sensitivity("all",20,20)
dist_sen.set_sensitivity("1",100,100)
dist_sen.set_sensitivity("2",100,100)
dist_sen.set_sensitivity("3",100,100)
#dist_sen.set_sensitivity("4",100,100)
#print(dist_sen.Parameters)
dist_sen.cmd_mode = 0
#print (dist_sen.cmd_mode)
 
time_value = None
temp = None
counter = 0
while True:
    dist_sen.collect_data()
    print ("Operation Type: {}".format(dist_sen.W_type))
    print ("Targetting Object: {}".format(dist_sen.target))
    print ("Moving Distance: {} cm".format(dist_sen.move_dist))
    print ("Moving Sensitivity: {}".format(dist_sen.move_sen))
    print ("Stable Distance: {} cm".format(dist_sen.stable_dist))
    print ("Stable Sensitivity: {}".format(dist_sen.stable_sen))
    print ("Measuring Distance: {} cm".format(dist_sen.M_dist))
        
    if dist_sen.target == "Both target":
        if dist_sen.move_dist >= dist_sen.stable_dist:
            data = dist_sen.move_dist
        else:
            data = dist_sen.stable_dist
    elif dist_sen.target == "Moving target":
        data = dist_sen.move_dist
    elif dist_sen.target == "Stable target":
        data = dist_sen.stable_dist
        if data == 8:
            data = dist_sen.move_dist
    else:
        data = None
    
    if data != None:
        
        if data > 65 and data < 110:
            temp = time.time()
            #temp = 1697296776
            structure_time = time.localtime(temp)
            if structure_time.tm_wday > 4:
                print("Weekend - Alert 1")
            else:
                print ("Weekdays")
                if structure_time.tm_hour < 9 or structure_time.tm_hour > 17:
                    print ("Not in Office Hours - Alert 2")
                else:
                    print ("Office Hours")
                    if time_value is None:
                        time_value = temp
        else:
            counter += 1
            if temp is not None:
                counter  = 0
                temp = None
            #print (counter)
            if counter > 5:
                temp = time.time()
                difference = temp - time_value
                print ("You have looked on the screen for {} seconds".format(difference))
                break
               
    time.sleep(0.1)