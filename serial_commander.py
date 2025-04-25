import serial
import threading
import queue
from serial.tools import list_ports
from collections import namedtuple

serialCommanderDataPoint = namedtuple("serialCommanderDataPoint", "output input kp ki kd setpoint error gripstate")

class SerialCommander:
    def __init__(self, port="COM3", baudrate=115200):
        self.availablePorts = list_ports.comports()
        self.port = None
        self.baudrate = baudrate
        self.queue = queue.Queue()
        self.running = False
        try:
            self.port = serial.Serial(port=port, baudrate=baudrate, timeout=1)
            self.running = True
            threading.Thread(target=self._read_loop, daemon=True).start()
        except Exception as e:
            print(f"Error opening serial port: {e}")

    def printAvailablePorts(self):
        for availablePort in self.availablePorts:
            print(availablePort)

    def close(self):
        self.running = False
        if self.port:
            self.port.close()

    def _read_loop(self):
        while self.running and self.port:
            try:
                # dataPoint = self.readDataPoint()
                # if dataPoint:
                    # self.queue.put(dataPoint)
                    # print(dataPoint)
                rawString = self.port.readline().decode("utf-8").strip()
                if rawString:
                    self.queue.put(rawString)
            except:
                continue

    def get_event(self):
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            return None

    def getDataPoint(self):
        if self.port is None:
            return None
        try:
            rawString = self.port.readline().decode("utf-8")
            splitData = rawString.split(",")
            if len(splitData) != 8:
                return None
            return serialCommanderDataPoint(float(splitData[0]),
                                            float(splitData[1]),
                                            float(splitData[2]),
                                            float(splitData[3]),
                                            float(splitData[4]),
                                            float(splitData[5]),
                                            float(splitData[6]),
                                            splitData[7].strip())
        except:
            return None

    def setSetPoint(self, setPointValue):
        if self.port:
            self.port.write('s{:f}\r\n'.format(setPointValue).encode())
            print(setPointValue)

    def setAutomaticMode(self):
        if self.port:
            self.port.write('a\r\n'.encode())
