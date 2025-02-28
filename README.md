# Executing Antelope
To clone the repository execute - 
```console
$ git clone https://github.com/subhrendu1987/AntelopeTraining
```

# Dependency Installation for Environment
## Kernel compilation
```console
$ sudo apt install git fakeroot build-essential ncurses-dev xz-utils libssl-dev bc flex libelf-dev bison
$ sudo apt install dwarves
$ sudo mkdir -p /usr/local/src/debian
$ sudo apt install linux-source
$ sudo cp -v /usr/src/linux-source-*/debian/canonical-*.pem /usr/local/src/debian/
$ sudo apt purge linux-source*
```
## Mininet Installation
In order to install mininet on your system you could follow [instructions here](https://mininet.org/download/),
or simply execute the following instructions on your ubuntu device - 
```console
$ sudo apt install python3-pip
$ sudo apt-get install mininet
$ wget https://www.openvswitch.org/releases/openvswitch-3.2.0.tar.gz
$ tar -xvf openvswitch-3.2.0.tar.gz
$ cd openvswitch-3.2.0
$ ./boot.sh 
$ ./configure --prefix=/usr --localstatedir=/var  --sysconfdir=/etc --enable-ssl --enable-Werror CC=gcc
$ make
$ sudo make install
```
Restart and try executing **sudo mn** to verify your installation.

# Modify and Build kernel
Before you being with execution of antelope, you will have to recompile the
linux kernel on your system with the file modifications mentioned below
The instructions have been written for kernel modifications on the ubuntu OS.
In case you are using any other OS, please refer to the instructions to compile
the kernel on the required OS.

You need to first download the linux kernel file using the following link - 
```console
$ wget https://cdn.kernel.org/pub/linux/kernel/vA.x/linux-A.B.C.tar.xz
$ tar -xvf linux-A.B.C.tar.xz
```
where A, B, C refer to the version number that you wish to download. These
instructions work only on Ubuntu Distros hvaing version > 20.04, and kernel
versions > 5.15. Please be sure to download the kernel version accordingly.
We use kernel 5.15.148 for compilation on a 22.04 ubuntu setup.
```console
$ wget https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-5.15.148.tar.gz
$ tar -xvf linux-5.15.148.tar.gz
```
Build the kernel

```console
$ lsb_release -a
No LSB modules are available.
Distributor ID:	Ubuntu
Description:	Ubuntu 22.04.4 LTS
Release:	22.04
Codename:	jammy

$ cat /proc/version
Linux version 6.1.38 (idrbt@idrbt) (gcc (Ubuntu 9.4.0-1ubuntu1~20.04.1) 9.4.0, GNU ld (GNU Binutils for Ubuntu) 2.34) #2 SMP PREEMPT_DYNAMIC Wed Aug  2 11:29:05 IST 2023
```

Directory Structure: 
```
/home/ebpf/GIT --|- AntelopeTraining
                  |- linux-5.15.148
```
Once all the dependencies have been installed, add the modifications mentioned as
follows - 

* The following lines need to be added in the `include/uapi/linux/bpf.h` file enum in the kernel folder containing all the bpf_sock_ops
entries. You could search for `bpf_sock_ops` and look for an enum containing
BPF_SOCK_OPS_ACTIVE_ESTABLISHED_CB flag. You could use the 
```c
BPF_SOCK_OPS_TCP_ACK_CB,
BPF_SOCK_OPS_TCL_CLOSE_CB,
BPF_BBR_ENTER,
```
Otherwise execute the following commands
```console
$ cd linux-5.15.148
$ cp ../AntelopeTraining/kernel_files/5.15.148/bpf.h ./include/uapi/linux/bpf.h
$ cp ../AntelopeTraining/kernel_files/5.15.148/bpf.h ./tools/include/uapi/linux/bpf.h
$ cp ../AntelopeTraining/kernel_files/5.15.148/bpf.h ./include/uapi/linux/bpf.h

$ diff  ../AntelopeTraining/kernel_files/5.15.148/bpf.h ./include/uapi/linux/bpf.h
$ diff ../AntelopeTraining/kernel_files/5.15.148/bpf.h ./include/uapi/linux/bpf.h
$ diff ../AntelopeTraining/kernel_files/5.15.148/bpf.h ./tools/include/uapi/linux/bpf.h
```

* Next, open the `net/ipv4/tcp.c` file in the kernel folder and add the following - 
```c
// Inside the tcp_sendmsg function
tcp_call_bpf(sk, BPF_SOCK_OPS_TCP_ACK_CB, 0, NULL);
// Inside the tcp_close_state function
tcp_call_bpf(sk, BPF_SOCK_OPS_TCL_CLOSE_CB, 0, NULL);
```
Otherwise 
```console
$ cp ../AntelopeTraining/kernel_files/5.15.148/tcp.c ./net/ipv4/tcp.c
$ diff ../AntelopeTraining/kernel_files/5.15.148/tcp.c ./net/ipv4/tcp.c
```

* The files we have modified are present in the folder **kernel_files**. You can
refer to these files for making modifications in your kernel as well.
* You can also copy the .config file present in the folder to apply the same
configuration for your kernel as well - 
```console
$ cp ../AntelopeTraining/kernel_files/5.15.148/config-5.15.148 ./.config
$ diff ../AntelopeTraining/kernel_files/5.15.148/config-5.15.148 ./.config
```

* Once all the changes are made, execute the following in order to compile and install the kernel.
```console
$ make -j$(nproc)
$ sudo make modules_install
$ sudo make headers_install
$ sudo make install
$ sudo update-grub
```
* If received error releated to vmlinuz
  ```console
  FAILED: load BTF from vmlinux: No such file or directory
  make: *** [Makefile:1227: vmlinux] Error 255
  make: *** Deleting file 'vmlinux'
  ```

  ```console
  $ apt install dwarves
  $ sudo cp /sys/kernel/btf/vmlinux /usr/lib/modules/`uname -r`/build/
  ```

* Reboot your system to see the newly installed kernel. You can select the newly
installed kernel version on your grub screen. In case your grub screen is not
visible(happens generally when the system is not dual booted), you can add the
following changes in your /etc/default/grub file.
```diff
< GRUB_TIMEOUT=0
...
> GRUB_TIMEOUT=10
...
< GRUB_TIMEOUT_STYLE=hidden
...
> GRUB_TIMEOUT_STYLE=menu
...

```
Otherwise
```console
$ cd ~/GIT
$ git clone https://github.com/subhrendu1987/easy-grub-selctor
$ cd easy-grub-selctor
$ sudo sh change_grub_entries.sh
```
# Verify kernel modification
## To install bpftools
```console
$ cd ~/GIT
$ git clone --recurse-submodules https://github.com/libbpf/bpftool.git ./bpftool
$ cd bpftool/src/
$ make
$ sudo make install
```

## To install bcc on your system
```console
$ cd ~/GIT
$ sudo apt-get install bpfcc-tools zip bison build-essential cmake flex git libedit-dev \
  libllvm14 llvm-14-dev libclang-14-dev python3 zlib1g-dev libelf-dev libfl-dev python3-setuptools \
  liblzma-dev libdebuginfod-dev arping netperf iperf
$ git clone https://github.com/iovisor/bcc.git ./bcc
$ mkdir ./bcc/build; cd ./bcc/build
$ cmake ..
$ make
$ sudo make install
$ cmake -DPYTHON_CMD=python3 .. # build python3 binding
$ pushd src/python/
$ make
$ sudo make install
$ popd
```
You can also follow the bcc installation instructions at [bcc](https://github.com/iovisor/bcc/blob/master/INSTALL.md#ubuntu---source)

## To Install python libraries
```console
$ cd ~/GIT/AntelopeTraining/
$ pip install -r requirements.txt
```
Please be sure to include the following flags to the /usr/include/linux/bpf.h
file on your system as well after the linux compilation has been completed since the bpf.h file is
apparently not updated when we switch to the kernel with modifications.
```c
BPF_SOCK_OPS_TCP_ACK_CB,
BPF_SOCK_OPS_TCL_CLOSE_CB,
BPF_BBR_ENTER,
```
In order to execute the program, you must first compile the required files - 
```console
$ cd AntelopeTraining
$ make
```

To begin execution - 
```bash
$ mkdir /tmp/cgroupv2
$ sudo mount -t cgroup2 none /tmp/cgroupv2
$ sudo mkdir -p /tmp/cgroupv2/foo
$ sudo echo $$ >> /tmp/cgroupv2/foo/cgroup.procs
$ ./load.sh
$ sudo python3 recvAndSetCC.py
```

To see the output of the bpf program execute - 
```console
$ ./trace.sh
```

To unload the attached program run - 
```console
$ ./unload.sh
```


# Antelope Initial Training Data
This doc explains generating the initial training data required to train the
XGBoost models for predicting Congestion Control rewards.
Setup the python environment, and install the python module requirements
```console
$ cd AntelopeTraining
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
```

## Collecting traindata using mininet
Once mininet is installed, you can create a dumbbell topology for your mininet
consisting of 4 hosts and 2 switches using the python script provided - 
```bash
sudo python mininet_script/dumbbell_topology.py
```
You can also adjust the required parameters of the hosts and switches within the python script
accordingly.

To generate data for training, execute the following - 
```
mininet> xterm h1 h1 h2 h2 h3 h4
```
Inside one of each h1 and h2 terminals, execute 
```bash
dd if=/dev/urandom of=output_file#  bs=1G count=1 iflag=fullblock # Generate test file of 1gb size 
#Setup desired congestion control
sudo modprobe -a tcp_<congestion_control>
sudo sysctl net.ipv4.tcp_congestion_control='<congestion_control>'
python -m http.server
```
This should generate a python server on both hosts and set the CC accordingly.

On the other two terminals opened of h1 and h2 each you can now track the packets
using the following commands - 
```bash
cd ..
# For h1
sudo python getSocketInfo.py > traindata/<h1_congestion>_<h2_congestion>.txt
# For h2
sudo python getSocketInfo.py > traindata/<h2_congestion>_<h1_congestion>.txt
```
Or any other name that helps you differentiate between the various files we
would be generating.

Create traffic using the following commands - 
```bash
# For h3
wget https://10.0.0.2:8000/output_file#
# For h4
wget https://10.0.0.1:8000/output_file#
```
The traffic is generated and the packet data is continuously stored in the
files.

Once all the required files are generated, run the following commands to
assemble all generated data together - 
```bash
cd traindata/
touch <congestion>_socket.txt #Generate data files for all necessary congestion control algorithms
cat <congestion>_*.txt > <congestion>_socket.txt # Do this for all CCs
```
This way all the data gets assembled into a single file for each congestion
control

### Training data file format
```
<TIMESTAMP> <SADDR> <SPORT> <DADDR> <DPORT> <SRTT> <MDEV> <MIN_RTT> <INFLIGHT> <TOTAL_LOST> <TOTAL_RETRANS> <RCV_BUF> <SND_BUF> <SND_CWND> <TCPSTATE[EVENT.STATE]> <STATE[EVENT.TCP_STATE]> <SK_PACING_RATE> <SK_MAX_PACING_RATE> <DELIVERED>
1516617628 3.0.0.10 34922 1.0.0.10 8000 631763 159635 48628 0 0 0 1277152 87380 10 ESTABLISHED open 366719 18446744073709551615 2
1516673074 1.0.0.10 8000 3.0.0.10 34922 1060641 20381 36701 58 45 35 87380 913920 56 ESTABLISHED open 641687 18446744073709551615 52375
```
## Processing Training Data
1. Get the socket information in the form **traindata/[cc-algo]_socket.txt**
> Eg. traindata/cubic_socket.txt, traindata/bbr_socket.txt
 
2. In generateTrainingData.py, change the following lines to suit the cc
   algorithm:
```
# NOTE: Change the CC algorithm and batch size here
CCNAME = "cubic"
BATCHSIZE = 20
```
Then, run generateTraindata.py --> training data will be stored as:
**traindata/[cc-algo]_output.txt**

3. In order to build the ML models, change the following lines in ModelTrain.py:
```
# NOTE: Change the congestion algorithm here
CCNAME = "cubic"
CAL_ACCURACY = 1
```

On running ModelTrain.py, models will be stored in the **traindata/models** folder


## Running the application
Once your system has successfully booted into your kernel, install the following on your machine before you begin executing the
application - 

```bash
sudo apt-get install git make
```
To install bpftools - 
```bash
git clone --recurse-submodules https://github.com/libbpf/bpftool.git ~/bpftool
cd ~/bpftool/src/
make
make install
```

To install bcc on your system - 
```bash
sudo apt-get install bpfcc-tools zip bison build-essential cmake flex git libedit-dev \
  libllvm14 llvm-14-dev libclang-14-dev python3 zlib1g-dev libelf-dev libfl-dev python3-setuptools \
  liblzma-dev libdebuginfod-dev arping netperf iperf
git clone https://github.com/iovisor/bcc.git ~/bcc
mkdir ~/bcc/build; cd ~/bcc/build
cmake ..
make
sudo make install
cmake -DPYTHON_CMD=python3 .. # build python3 binding
pushd src/python/
make
sudo make install
popd
```
You can also follow the bcc installation instructions at [bcc](https://github.com/iovisor/bcc/blob/master/INSTALL.md#ubuntu---source)

Install all the required python libraries using requirements.txt - 
```bash
pip install -r requirements.txt
```
Please be sure to include the following flags to the /usr/include/linux/bpf.h
file on your system as well after the linux compilation has been completed since the bpf.h file is
apparently not updated when we switch to the kernel with modifications.
```c
BPF_SOCK_OPS_TCP_ACK_CB,
BPF_SOCK_OPS_TCL_CLOSE_CB,
BPF_BBR_ENTER,
```
In order to execute the program, you must first compile the required files - 
```bash
cd ~/antelope/
make
```

To begin execution - 
```bash
mkdir /tmp/cgroupv2
sudo mount -t cgroup2 none /tmp/cgroupv2
sudo mkdir -p /tmp/cgroupv2/foo
echo $$ | sudo tee -a /tmp/cgroupv2/foo/cgroup.procs
./load.sh
sudo python3 recvAndSetCC.py
```

To see the output of the bpf program execute - 
```bash
./trace.sh
```

To unload the attached program run - 
```bash 
./unload.sh
```