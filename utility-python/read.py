import serial
import time
ser = serial.Serial('/dev/ttyS0', 115200)
while 1:
	print ser.readline()
	print time.localtime()
