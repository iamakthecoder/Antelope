# Generate training data (data.txt) from socket struct info
import numpy as np
import time
import copy
#import subprocess
import argparse

parser = argparse.ArgumentParser(description='Train Data Generation Script')
parser.add_argument('--cc', type=str, required=True, help='Congestion control algorithm')
parser.add_argument('--file', type=str, required=True, help='Name of the data file')

args = parser.parse_args()

CCNAME = args.cc
EBPF_DATAFILENAME = args.file

ccNameMap = {0: CCNAME}
BATCHSIZE = 20

ipCongMap = {} # dictionary (set of key:value pairs)

class OnlineServer:
    def __init__(self, bufferSize, ccName):
        self.bufferSize = bufferSize
        self.buffer = []
        self.read = 0
        self.write = 0
        self.ccName = ccName
        self.staticCount = BATCHSIZE
        self.trainLawData = {}
        self.flowStaticData = {}
        self.flowStaticData[0] = {}

    def runTshark(self):
        #cmd = ["python3", "getSocketInfo2.py"]
        #proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        print("Starting Tshark")
        filename = "traindata/" + CCNAME + "_socket.txt"
        file = open(filename, "r")
        for line in file:
            try:
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
                print("subprocess error [runTshark]: " + str(e))
        print("runTshark Done")
        return

    def getData(self, line):
        data = {}
        param = line.split()
        # print ("param: " + str(param))
        data['time'] = int(param[0])
        data['Source'] = param[1]
        data['Destination'] = param[3]
        data['port'] = param[4]
        data['rtt'] = int(param[5])
        data['mdevRtt'] = int(param[6])
        data['minRtt'] = int(param[7])
        data['bytes_in_flight'] = int(param[8])
        data['lost'] = int(param[9])
        data['retrans'] = int(param[10])
        data['rcv_buf'] = param[11]
        data['snd_buf'] = int(param[12])
        data['snd_cwnd'] = int(param[13])
        data['status'] = param[14]
        data['pacing_rate'] = param[16]
        data['delivered'] = param[18]
        return data

    # def calIPPred(self, ipKey, val):
    #     # will return ipCongMap[ipKey] or [0,0,0,0] if ipKey key not found
    #     congVal = ipCongMap.get(ipKey, [0, 0, 0, 0])
    #     for index in range(len(congVal)):
    #         congVal[index] *= alf
    #     congVal[val] += 1
    #     ipCongMap[ipKey] = congVal
    #     predic = int(congVal.index(max(congVal)))
    #     print("ipKey: " + str(ipKey) + " ip predic: " + str(predic))
    #     print(str(ipCongMap))
    #     return predic

    def readPacketData(self):

        # filename = "traindata/" + CCNAME + "_socket.txt"
        filename = EBPF_DATAFILENAME
        file = open(filename, "r")

        for line in file:
            readData = self.getData(line)
            key = readData['port']
            self.read += 1
            try:
                # for a new port no
                if key not in self.flowStaticData:
                    self.flowStaticData[key] = self.newFlowStaticData()
                    t = time.time()
                    self.flowStaticData[key]['beginTime'] = int(round(t * 1000))
                # same as if "LAST_ACK" in readData["status"]:
                # i.e. if we get the last ACK on a specific port no
                elif readData['status'].__contains__("LAST_ACK"):
                    # print("enter last")
                    self.flowStaticData[key]['last'] = True
                    t = time.time()
                    self.flowStaticData[key]['time'] = int(round(t * 1000))
                    self.intervalAction(self.flowStaticData[key]['countIndex'], key) #INTERVAL_ACTION
                    del self.flowStaticData[key]
                # new ACKs for an existing port no
                if key in self.flowStaticData:
                    # append parameters of new ACK
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
                    # update max pacing rate
                    if ("max_pacing_rate" not in self.flowStaticData[key] or self.flowStaticData[key]['max_pacing_rate'] == 0):
                        self.flowStaticData[key]['max_pacing_rate'] = int(readData['pacing_rate'])
                    else:
                        self.flowStaticData[key]['max_pacing_rate'] = max(int(readData['pacing_rate']), self.flowStaticData[key][ 'max_pacing_rate'])
                    self.flowStaticData[key]['number'] += 1
                    # if we get more than staticCount (or N=20) ACK packets
                    # for the same port no
                    if self.flowStaticData[key]['number'] > self.staticCount:
                        t = time.time()
                        self.flowStaticData[key]['time'] = int(round(t * 1000))
                        countIndex = self.flowStaticData[key]['countIndex']
                        self.intervalAction(countIndex, key) #INTERVAL_ACTION
                        self.flowStaticData[key] = self.newFlowStaticData()
                        countIndex += 1 # countIndex is updated here
                        self.flowStaticData[key]['countIndex'] = countIndex
            except Exception as e:
                print("error: " + str(e))


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

    # called on either (1) the Last ACK on a port number or
    #                  (2) the 20th ACK on a port number
    def intervalAction(self, countIndex, key):

        preCountIndex = countIndex - 1
        preTrainKey = key + "_" + str(preCountIndex)
        # e.g. if countIndex = 0, key = 8888 --> preTrainKey = 8888_-1
        preTrainData = None
        if preTrainKey in self.trainLawData:
            preTrainData = self.trainLawData[preTrainKey]

        data = self.calTrainData(key, preTrainData)
        # print("countIndex: " + str(countIndex) + " rtt: " + str(data['meanRTT']))
        beta = 512
        if countIndex < 9:
            beta = pow(2, countIndex)
        if data['minRTT'] * beta > data['meanRTT']:
            rtt = data['minRTT']
        else:
            rtt = data['meanRTT']

        # if known port no
        if preTrainKey in self.trainLawData:
            reward = self.calReward(data, rtt)
            # data of previous batch, reward of next
            self.trainLawData[preTrainKey]['result'] = reward

        # on N(=20)th packet
        if "last" not in self.flowStaticData[key]:
            trainKey = key + "_" + str(countIndex)
            self.trainLawData[trainKey] = data
            self.trainLawData[trainKey]['rtt'] = rtt
            # NOTE: [testing] Hardcode for "cubic"
            self.trainLawData[trainKey]['predictCC'] = 0

    # calculates parameters for current batch of N(=20) ACK packets
    # or batch till last packet
    def calTrainData(self, key, preData):
        result = {}
        maxDelivered = np.max(self.flowStaticData[key]['delivered'])
        if preData is None: # the port has got first 20 packets, or less than 20 with a last ACK packet
            transTime = self.flowStaticData[key]['time'] - self.flowStaticData[key]['beginTime']
            delivered = maxDelivered
            lost = self.flowStaticData[key]['lost']

        else:
            transTime = self.flowStaticData[key]['time'] - preData['time']
            delivered = maxDelivered- preData['delivered']
            lost = self.flowStaticData[key]['lost']-preData['totalLost']

        if transTime == 0:
            throughput = float(delivered)
        else:
            throughput = float(delivered) / float(transTime)

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

    def bashWriteTrainData(self):
        # acquire default params: (blocking=True, timeout=-1)
        #lock.acquire()
        trainDataCCMap = {}
        delKeys = []
        keys = copy.deepcopy(list(self.trainLawData.keys()))

        for cc in ccNameMap.keys():
            trainDataCCMap[cc] = []

        # print("\nbatchwrte: ")
        for key in keys:
            # if reward has not been calculated for current key
            if "result" not in self.trainLawData[key].keys() or self.trainLawData[key]['result'] == '':
                continue
            delKeys.append(key)
            data = self.trainLawData[key]
            # the data that we need to train the model with
            termTrainData = [int(data['minRTT']), float(data['mdevRTT']), float(data['meanRTT']),float(data['rtt']),
                             float(data['throughput']),float(data['lost']),float(data['meanPacingRate']),
                             float(data['result'])]

            trainDataCCMap[int(data['predictCC'])].append(termTrainData)
        for cc in trainDataCCMap.keys():
            if (trainDataCCMap[cc].__len__() > 0):
                fileName = "traindata/" + ccNameMap[cc] + "_output.txt"
                # print(f"Adding {trainDataCCMap[cc].__len__()} lines")
                # write training data in respective CC's file
                self.writeData(fileName, trainDataCCMap[cc])
        # print("write end " + str(delKeys))
        for key in delKeys:
            # print("delKey: " + key)
            del self.trainLawData[key]
        #lock.release()

    # write training data in respective CC's file
    def writeData(self, path, data):
        with open(path, 'a') as f:
            # print("open path")
            try:
                writeData = np.array(data)
                np.savetxt(f, writeData, delimiter=" ")
            except Exception as e:
                print(e.message)

    def calReward(self, trainData, rtt):
        '''
        print(" meanRTT: " + str(trainData['meanRTT']) + " minRTT: " + str(
            trainData['minRTT']) + " rtt: " + str(rtt) + " max throughput: " + str(trainData['maxThroughput']))
        '''
        # max_pacing_rate = trainData['max_pacing_rate'] / 1000000
        # print("Cal reward: throughput: " + str(trainData['throughput']) +
        #       " lost: " + str(trainData['lost']) +
        #       " rtt: " + str(rtt) + " min_rtt: " + str(trainData['minRTT']) +
        #       " max pacing rate: " + str(max_pacing_rate))
        reward = ((trainData['throughput'] * 1000 - trainData['lost']) * trainData['minRTT']) / (rtt*trainData['max_pacing_rate'])
        reward = reward * 1000000 # TODO: check this; scaling factor
        return reward

online = OnlineServer(200, CCNAME)
# online.runTshark()
online.readPacketData()
online.bashWriteTrainData()
