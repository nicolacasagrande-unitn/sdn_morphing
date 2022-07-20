# Morphing Network Slices

This project has been developed for the Softwarized and Virtualized Mobile Networks course by:
* Lorenzo Antonio Riva 
* Firas Soussane 
* Nicola Casagrande

## Introduction
This project shows how to use RYU SDN controller to dynamically change the topology of a predefined network. The network we take into consideration is composed of two sub-networks, each of them is made up of five switches, one of them is in the middle and is connected to all the other four switches that may also be connected to other switches or hosts. The physical topology of the two subnetworks is thus a star topology. <br>
Every host can communicate with all the other hosts and can host services, the topology of the network changes based on the type of packet that is sent by the hosts, the topology change is not physical, in fact the physical topology remains the same through the whole process but the RYU controller simulates the different topologies by routing the packets through different paths based on their type.

Hosts can use three types of different services: 
* documents -> TCP packet with 8880 as destination port 
* messages -> TCP packet with 8888 as destination port 
* video -> UDP packet with 9999 as the destination port

For documents packets the upper subnet will use a star topology and the lower one will use a ring topology. <br>
For messages packets the upper subnet will use a line topology and the lower one will use a star topology. <br>
For video packets the upper subnet will use a rign topology and the lower one will use a line topology. <br>

Every switch that is reached by the packet is printed in a different color in the terminal:
* if the packet goes through the upper line topology it is printed in GREEN
* if the packet goes through the upper ring topology it is printed in YELLOW
* if the packet goes through the upper star topology it is printed in BLUE
* if the packet goes through the lower line topology it is printed in MAGENTA
* if the packet goes through the lower ring topology it is printed in CYAN
* if the packet goes through the lower star topology it is printed in RED
* in all the other cases the color is WHITE

# The Topology
![alt text](https://github.com/nicolacasagrande-unitn/sdn_morphing/blob/main/network_topology.png)

## How to Run 

You can run the emulation process by using the following commands:

1. From the comnetsemu repository start the virtual machine by running:
    ```bash
    vagrant up comnetsemu
    ```
2. Open two different terminals and connect to the comnetsemu virtual machine in both of them by running:
    ```bash
    vagrant ssh comnetsemu
    ```
3. In the first terminal clear Mininet using the following command:
    ```bash
    sudo mn -c
    ```
4. In the second terminal run the RYU controller in the background with:
    ```bash
    ryu-manager morphing_controller.py &
    ```
5. In the first terminal run the following command to start mininet and create the topology:
    ```bash
    sudo python3 network.py
    ```
    If xterm does not work you can try to run the network with this alternative command:
    ```bash
    sudo -E python3 network.py
    ```

## How to Test
1. We can test if the network topology has been created correctly using the following command in the mininet console:
    ```bash
    links
    ```
### Testing the documents service

1. In the mininet console run two terminals for h2 and h4 using:
    ```bash
    xterm h2 h4
    ```
2. To initialize h4 as a server and start listening for TCP packets on port 8880 run the following command in the h4 terminal:
    ```bash
    iperf -s -p 8880 -b 10M
    ```
3. To send a TCP packet on port 8880 to server h4 from host h2 run the following command:
    ```bash
    iperf -c 10.0.0.4 -p 8880 -b 10M -t 1 -i 1 
    ```
![alt text](https://github.com/nicolacasagrande-unitn/sdn_morphing/blob/main/Test1.png)

### Testing the messages service

1. In the mininet console run two terminals for h1 and h3 using:
    ```bash
    xterm h1 h3
    ```
2. To initialize h1 as a server and start listening for TCP packets on port 8888 run the following command in the h1 terminal:
    ```bash
    iperf -s -p 8888 -b 10M
    ```
3. To send a TCP packet on port 8888 to server h1 from host h3 run the following command:
    ```bash
    iperf -c 10.0.0.1 -p 8888 -b 10M -t 1 -i 1 
    ```
![alt text](https://github.com/nicolacasagrande-unitn/sdn_morphing/blob/main/Test2.png)

### Testing the video service

1. In the mininet console run two terminals for h5 and h6 using:
    ```bash
    xterm h5 h6
    ```
2. To initialize h5 as a server and start listening for UDP packets on port 9999 run the following command in the h5 terminal:
    ```bash
    iperf -s -u -p 9999 -b 10M
    ```
3. To send a UDP packet on port 9999 to server h5 from host h6 run the following command:
    ```bash
    iperf -c 10.0.0.5 -u -p 9999 -b 10M -t 1 -i 1 
    ```
![alt text](https://github.com/nicolacasagrande-unitn/sdn_morphing/blob/main/Test3.png)

