import subprocess
import numpy as np
import threading
import time
import socket
import pickle
import struct
import copy
import threadpool
from ctypes import *
from apscheduler.schedulers.blocking import BlockingScheduler
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
import sys
import logging
import os

lock = threading.Lock()
ipCongMap = {}
predicMap = {}
preCCMap = {}
alf = 0.9

#for TESTING
LOGGING_FILE = "testing/validation_logs_antelope" 
log = None
if LOGGING_FILE is not None and os.path.exists(LOGGING_FILE): # Clear the log file
    with open(LOGGING_FILE, 'w'):
        pass
if LOGGING_FILE is not None:
    log = open(LOGGING_FILE, 'a')

# NOTE: Append the congestion control algorithms (order is important; should be same as that in transfer_cc.c)
ccNameMap = {0: "cubic",
             1: "bbr",
             2: "westwood",
             3: "illinois",
             4: "vegas"}

ccFileMap = {0: "models/cubic.pickle",
             1: "models/bbr.pickle",
             2: "models/westwood.pickle",
             3: "models/illinois.pickle",
             4: "models/models_3/vegas.pickle"}

pickleMap = {} # {cc: model} where cc is the cca index and model is the trained model (taken from the path in ccFileMap)

class OnlineServer:
    def __init__(self, bufferSize, ccName):
        self.bufferSize = bufferSize
        self.buffer = []
        self.read = 0
        self.write = 0
        self.ccName = ccName
        self.sigma = 1
        self.threadPool = ThreadPoolExecutor(max_workers=6)
        self.staticCount = 20
        self.trainLawData = {}
        self.flowStaticData = {}
        self.flowStaticData[0] = {}
        self.changeCong = CDLL('./transfer_cc.so')
        print("Loading pickle files")
        for cc in ccFileMap:
            with open(ccFileMap[cc], "rb") as fr:
                p = pickle.load(fr)
                pickleMap[cc] = p
        print("Pickle files loaded")

    def runTshark(self):
        cmd = ['python3', 'getSocketInfo.py']
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        print("Running Tshark (getSocketInfo.py)...")

        while True:
            try:
                lawline = proc.stdout.readline()
                line = str(lawline, encoding="utf-8")
                line = line.strip()

                if not line:
                    None
                else:
                    if self.write < self.bufferSize:
                        self.buffer.append(line)
                        self.write += 1
                    else:
                        index = self.write % self.bufferSize
                        self.buffer[index] = line
                        self.write += 1
            except Exception as e:
                print("run shell error " + str(e))


    def readPacketData(self):
        print("Reading packet data...")
        while True:
            if self.read < self.write:
                index = self.read % self.bufferSize
                line = self.buffer[index]
                self.read += 1

                readData = self.getData(line) 
                key = readData["port"] # TODO: this is only taking the dport as the key, check to include saddr, daddr, lport as well...

                try:
                    if key not in self.flowStaticData:
                        self.flowStaticData[key] = self.newFlowStaticData()
                        t = time.time()
                        self.flowStaticData[key]['beginTime'] = int(round(t * 1000))
                    elif readData['status'].__contains__("LAST_ACK"):
                        self.flowStaticData[key]['last'] = True
                        t = time.time()
                        self.flowStaticData[key]['time'] = int(round(t * 1000))
                        self.intervalAction(self.flowStaticData[key]['countIndex'], key)
                        del self.flowStaticData[key]
                        del predicMap[key]
                        del preCCMap[key]

                    if key in self.flowStaticData:
                        self.flowStaticData[key]['delivered'].append(int(readData['delivered']))
                        self.flowStaticData[key]['rcvBuf'].append(int(readData['rcv_buf']))
                        self.flowStaticData[key]['sndBuf'].append(int(readData['snd_buf']))
                        self.flowStaticData[key]['sndCwnd'].append(int(readData['snd_cwnd']))
                        self.flowStaticData[key]['rtt'].append(int(readData['rtt']))
                        self.flowStaticData[key]['Destination'] = readData['Destination']
                        self.flowStaticData[key]['minRTT'] = readData['minRtt']
                        self.flowStaticData[key]['mdevRTT'] = readData['mdevRtt']
                        self.flowStaticData[key]['bytesInFlight'].append(int(readData['bytes_in_flight']))
                        self.flowStaticData[key]['lost'] = readData['lost']
                        self.flowStaticData[key]['retrans'] = readData['retrans']
                        self.flowStaticData[key]['pacing_rate'].append(int(readData['pacing_rate']))

                        if ("max_pacing_rate" not in self.flowStaticData[key] or self.flowStaticData[key]['max_pacing_rate']==0):
                            self.flowStaticData[key]['max_pacing_rate'] = int(readData['pacing_rate'])
                        else:
                            self.flowStaticData[key]['max_pacing_rate'] = max(int(readData['pacing_rate']),
                                                                              self.flowStaticData[key]['max_pacing_rate'])
                        self.flowStaticData[key]['number'] += 1

                        #for TESTING
                        if log is not None:
                            log.write(f"RTT : {self.read}: {readData['rtt']}\n")
                            log.write(f"CWND : {self.read}: {readData['snd_cwnd']}\n")
                            log.write(f"PACING RATE : {self.read}: {readData['pacing_rate']}\n")
                            log.flush()
                            os.fsync(log.fileno())

                        if self.flowStaticData[key]['number'] > self.staticCount:
                            t = time.time()
                            self.flowStaticData[key]['time'] = int(round(t * 1000))
                            countIndex = self.flowStaticData[key]['countIndex']
                            self.intervalAction(countIndex, key)     

                            self.flowStaticData[key] = self.newFlowStaticData()
                            self.flowStaticData[key]['countIndex'] = countIndex + 1                  
                        
                except Exception as e:
                    print("Error in readPacketData: " + str(e))
 
    def getData(self, line):
        data = {}
        param = line.split()
        data['Destination'] = param[3]
        data['Source'] = param[1]
        data['time'] = int(param[0])
        data['delivered'] = param[18]
        data['rtt'] = int(param[5])
        data['mdevRtt'] = int(param[6])
        data['minRtt'] = int(param[7])
        data['bytes_in_flight'] = int(param[8])
        data['port'] = param[4] # TODO: this is only reading the dport, should check for the lport as well?
        data['lost'] = int(param[9])
        data['retrans'] = int(param[10])
        data['rcv_buf'] = param[11]
        data['snd_buf'] = int(param[12])
        data['snd_cwnd'] = int(param[13])
        data['status'] = param[14]
        data['pacing_rate'] = param[16]
        return data
    
    def newFlowStaticData(self):
        flowStaticPerData = {}
        flowStaticPerData['time'] = 0
        flowStaticPerData['delivered'] =[]
        flowStaticPerData['Destination'] = ""
        flowStaticPerData['bytesInFlight'] = []
        flowStaticPerData['rcvBuf'] = []
        flowStaticPerData['sndBuf'] = []
        flowStaticPerData['pacing_rate'] = []
        flowStaticPerData['countIndex'] = 0
        flowStaticPerData['max_pacing_rate'] = 0
        flowStaticPerData['sndCwnd'] = []
        flowStaticPerData['rtt'] = []
        flowStaticPerData["retrans"] = 0
        flowStaticPerData["lost"] = 0
        flowStaticPerData["maxRTT"] = 0
        flowStaticPerData['minRTT'] = 0
        flowStaticPerData['mdevRTT'] = 0
        flowStaticPerData['number'] = 0
        flowStaticPerData['beginTime'] = 0
        return flowStaticPerData

    def intervalAction(self, countIndex, key):
        preCountIndex = countIndex - 1
        preTrainKey = key + "_" + str(preCountIndex)
        preTrainData = None
        if preTrainKey in self.trainLawData:
            preTrainData = self.trainLawData[preTrainKey]

        data = self.calTrainData(key, preTrainData)

        #for TESTING
        if log is not None:
            log.write(f"THROUGHPUT : {self.read}: {data['throughput']}\n")
            log.flush()
            os.fsync(log.fileno())

        beta = 512
        if countIndex < 9:
            beta = pow(2, countIndex)

        if data['minRTT'] * beta > data['meanRTT']:
            rtt = data['minRTT']
        else:
            rtt = data['meanRTT']

        if preTrainKey in self.trainLawData:
            reward = self.calReward(data, rtt)
            self.trainLawData[preTrainKey]['result'] = reward

        if "last" not in self.flowStaticData[key]:
            trainKey = key + "_" + str(countIndex)
            self.trainLawData[trainKey] = data
            self.trainLawData[trainKey]['rtt'] = rtt
            self.trainLawData[trainKey]['predictCC'] = self.predicCC(data, key, rtt)


    def calTrainData(self, key, preData):
        result = {}
        maxDelivered = np.max(self.flowStaticData[key]['delivered'])

        if preData is None:
            transTime = self.flowStaticData[key]['time'] - self.flowStaticData[key]['beginTime']
            delivered = maxDelivered
            lost = self.flowStaticData[key]['lost']
        else:
            transTime = self.flowStaticData[key]['time'] - preData['time']
            delivered = maxDelivered - preData['delivered']
            lost = self.flowStaticData[key]['lost']-preData['totalLost']

        if transTime == 0:
            throughput = float(delivered)
        else:
            throughput = float(delivered) / float(transTime)

        #for TESTING (to be removed): sometimes got negative throughput while testing
        if throughput < 0:
            if preData is None:
                log.write(f"ERROR: throughput < 0: maxDelivered = delivered: {maxDelivered}, transTime: {transTime}, self.flowStaticData[key][time] : {self.flowStaticData[key]['time']}, self.flowStaticData[key][beginTime] = {self.flowStaticData[key]['beginTime']}\n")
            else:
                log.write(f"ERROR: throughput < 0: delivered: {delivered} , maxDelivered: {maxDelivered}, preData[delivered]: {preData['delivered']}, transTime: {transTime}, self.flowStaticData[key][time] : {self.flowStaticData[key]['time']}, preData[time]: {preData['time']}\n")
            log.flush()
            os.fsync(log.fileno())
        else:
            if preData is None:
                log.write(f"CHECK: throughput >= 0: maxDelivered = delivered: {maxDelivered}, transTime: {transTime}, self.flowStaticData[key][time] : {self.flowStaticData[key]['time']}, self.flowStaticData[key][beginTime] = {self.flowStaticData[key]['beginTime']}\n")
            else:
                log.write(f"CHECK: throughput >= 0: delivered: {delivered} , maxDelivered: {maxDelivered}, preData[delivered]: {preData['delivered']}, transTime: {transTime}, self.flowStaticData[key][time] : {self.flowStaticData[key]['time']}, preData[time]: {preData['time']}\n")
            log.flush()
            os.fsync(log.fileno())

        #TODO : encountered negative throughput while testing, so added this condition; this is happening mostly due to the way (struct tcp_sock).delivered counter is maintained in case of retransmissions etc.
        if (preData is not None) and (throughput < 0):
            throughput = preData['throughput']

        result['Destination'] = self.flowStaticData[key]['Destination']
        result['meanPacingRate'] = np.mean(self.flowStaticData[key]['pacing_rate'])
        result['time'] = self.flowStaticData[key]['time']
        result['delivered'] = maxDelivered
        result['meanRTT'] = np.mean(self.flowStaticData[key]['rtt'])
        result["maxRTT"] = self.flowStaticData[key]['maxRTT']
        result['95th'] = np.percentile(self.flowStaticData[key]['rtt'], 95)
        result['minRTT'] = self.flowStaticData[key]['minRTT']
        result['mdevRTT'] = self.flowStaticData[key]['mdevRTT']
        result['retrans'] = self.flowStaticData[key]['retrans']
        result['max_pacing_rate'] = self.flowStaticData[key]['max_pacing_rate']
        result['lost'] = lost
        result['totalLost'] = self.flowStaticData[key]['lost']
        result['throughput'] = throughput
        if preData is None or throughput > preData['maxThroughput']:
            result['maxThroughput'] = throughput
        else:
            result['maxThroughput'] = preData['maxThroughput']

        return result
    
    def calReward(self, trainData, rtt):
        reward = ((trainData['throughput'] * 1000 - trainData['lost']) * trainData['minRTT']) / (rtt * trainData['max_pacing_rate'])
        reward = reward * 1000000 #TODO: check this; scaling factor
        return reward
    
    def predicCC(self, trainData, key, rtt):
        data = trainData

        #TODO: check this; original code uses data['maxRTT'] (which is actually never being set) for prediction, but uses 'rtt' for training
        # so, seems like a BUG! ...changing 'data['maxRTT']' to 'rtt' for prediction as well
        # termTrainData = [int(data['minRTT']), float(data['mdevRTT']), float(data['meanRTT']), float(data['maxRTT']),
        #                  float(data['throughput']), float(data['lost']), float(data['meanPacingRate'])]
        termTrainData = [int(data['minRTT']), float(data['mdevRTT']), float(data['meanRTT']), rtt,
                         float(data['throughput']), float(data['lost']), float(data['meanPacingRate'])]

        npData = np.array(termTrainData).reshape(1, 7)
        rewards = {}
        allTask = []
        for cc in pickleMap:
            allTask.append(self.threadPool.submit(self.runPredic, cc, rewards, npData))
        wait(allTask, return_when=ALL_COMPLETED)
        result = max(rewards, key=rewards.get)

        # result = 1 #TODO: for TESTING, REMOVE THIS!!!

        if not predicMap.__contains__(key):
            ccArray = []
        else:
            ccArray = predicMap[key]

        if not preCCMap.__contains__(key):
            preCC = None
        else:
            preCC = preCCMap[key]

        ccArray.append(result)
        predicMap[key] = ccArray

        if (preCC is not None) and (preCC == result or ccArray[-2] != result):
            return preCC
        
        preCCMap[key] = result
        ipKey = struct.unpack('!I', socket.inet_aton(data['Destination']))[0] #TODO: why only dest IP as key (bcoz sending 'key' as well in changeCong.update_congestion_hash() function)
        ipPredic = self.calIPPred(int(ipKey), int(result))
        ipkey_29MSB = int(ipKey) / 1000
        ipkey_3LSB = int(ipKey) % 1000

        # print(f"predicCC:: key: {int(key)}, ipkey_29MSB: {int(ipkey_29MSB)}, ipkey_3LSB: {int(ipkey_3LSB)}, result: {int(result)}") # TODO: remove this line
        self.changeCong.updateCongHash(int(key), int(ipkey_29MSB), int(ipkey_3LSB), 
                                        int(result), int(ipPredic))
        #for TESTING
        if log is not None:
            log.write(f"CC : {self.read}: {result}\n")
            log.flush()
            os.fsync(log.fileno())
        
        return result

    def calIPPred(self, ipKey, val):
        congVal = ipCongMap.get(ipKey, [0] * len(pickleMap))
        for index in range(len(congVal)):
            congVal[index] *= alf
        congVal[val] += 1
        ipCongMap[ipKey] = congVal
        predic = int(congVal.index(max(congVal)))
        return predic
        

    def runPredic(self, cc, rewards, npData):
        newModel = pickleMap[cc]
        y_pred = newModel.predict(npData).tolist()
        rewards[cc] = float(y_pred[0])
        

class tSharkThread(threading.Thread):
    def __init__(self, object):
        threading.Thread.__init__(self, name='tshark')
        self.object = object

    def run(self):
        self.object.runTshark()

class readThread(threading.Thread):
    def __init__(self, object):
        threading.Thread.__init__(self, name='read')
        self.object = object

    def run(self):
        self.object.readPacketData()


online = OnlineServer(200, "bbr")
tshark = tSharkThread(online)
read = readThread(online)
tshark.start()
read.start()
# online.scheduleWriteJob() #TODO: Not completed!
tshark.join()
read.join()
if log is not None:
    log.close()
