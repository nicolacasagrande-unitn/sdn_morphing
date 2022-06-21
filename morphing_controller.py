from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import udp
from ryu.lib.packet import tcp
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class TrafficSlicing(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TrafficSlicing, self).__init__(*args, **kwargs)
    
        ''' self.mac_port = {
            1: {"00:00:00:00:00:01": 3},
            2: {"00:00:00:00:00:01": 2},
            3: {"00:00:00:00:00:01": 1},
            4: {"00:00:00:00:00:01": 1},
            5: {"00:00:00:00:00:01": 1},
        }

        # out_port = slice_to_port[dpid][service]
        #1: UDP 9999, 2: TCP 8888, 3: OTHER
        self.service_slice = {
            1: {1: 1, 2: 2, 3: 2},
            2: {1: 1, 2: 1, 3: 1},
            3: {1: 1, 2: 2, 3: 3},
            4: {1: 1, 2: 1, 3: 2},
            5: {1: 1, 3: 1, 2: 2}
        }

        self.UDP_port = 9999
        self.TCP_port = 8888 '''

        self.UDP_port = 9999 # upper_part = ring lower_part = line 
        self.TCP1_port = 8880 # upper_part = star lower_part = ring 
        self.TCP2_port = 8888 # upper_part = line lower_part = star 

        self.mac_port = {
            2: {"00:00:00:00:00:01": 2},
            3: {"00:00:00:00:00:02": 2},
            11: {"00:00:00:00:00:07": 3, "00:00:00:00:00:06": 2},
            9: {"00:00:00:00:00:05": 2},
            7: {"00:00:00:00:00:03": 2},
            8: {"00:00:00:00:00:04": 2},
            5: {"00:00:00:00:00:07": 2, "00:00:00:00:00:06": 2}
        }

        self.upper_tcp1_topology = {
            1: {"00:00:00:00:00:01": 1, "00:00:00:00:00:02": 2, "00:00:00:00:00:03": 3, "00:00:00:00:00:04": 3, "00:00:00:00:00:05": 3, "00:00:00:00:00:06": 4, "00:00:00:00:00:07": 4 }
        }

        self.lower_tcp2_topology = {
            10: {"00:00:00:00:00:01": 1, "00:00:00:00:00:02": 1, "00:00:00:00:00:03": 2, "00:00:00:00:00:04": 3, "00:00:00:00:00:05": 4, "00:00:00:00:00:06": 1, "00:00:00:00:00:07": 1 }
        }

        self.line = {

        }

        self.ring = {

        }
        

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install the table-miss flow entry.
        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath, priority=priority, match=match, instructions=inst
        )
        datapath.send_msg(mod)

    def _send_package(self, msg, datapath, in_port, actions):
        data = None
        ofproto = datapath.ofproto
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src
        dpid = datapath.id
        prot = "OTHER"
        if pkt.get_protocol(udp.udp):
            prot = "UDP"
        elif pkt.get_protocol(tcp.tcp):
            prot = "TCP"
        #self.logger.info("+++++++++++++++++++++++++++++++++")
        #self.logger.info("ALL: DPID: %s ETHSRC: %s ETHDST: %s   PROT: %s", dpid, src, dst, prot)
       
        #controllo che lo switch sia in self.macport
        if dpid in self.mac_port:
            #controllo che la destinazione sia dentro a self.macport di quello switch 
            if dst in self.mac_port[dpid]:
                print(str(bcolors.OKCYAN) + str(dst) + " <== " + str(dpid) + str(bcolors.ENDC))
                out_port = self.mac_port[dpid][dst]
                actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
                match = datapath.ofproto_parser.OFPMatch(eth_dst=dst)
                self.add_flow(datapath, 1, match, actions)
                self._send_package(msg, datapath, in_port, actions)

            elif (pkt.get_protocol(tcp.tcp) and pkt.get_protocol(tcp.tcp).dst_port == self.TCP_port):

                

                slice_number = 2
                out_port = self.service_slice[dpid][slice_number]
                print(str(bcolors.OKGREEN)+ "TCP:" + str(dpid) + " ==> " + str(dst) + str(bcolors.ENDC) + " NEXT: " + str(out_port))
                match = datapath.ofproto_parser.OFPMatch(
                    in_port=in_port,
                    eth_dst=dst,
                    eth_src=src,
                    eth_type=ether_types.ETH_TYPE_IP,
                    ip_proto=0x06,  # tcp
                )
                actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
                self.add_flow(datapath, 1, match, actions)
                self._send_package(msg, datapath, in_port, actions)
                
                

            else:
                
                slice_number = 2
                if dpid == 3 or dpid == 4:
                    slice_number = 3
                
                out_port = self.service_slice[dpid][slice_number]
                match = datapath.ofproto_parser.OFPMatch(
                    in_port=in_port,
                    eth_dst=dst,
                    eth_src=src,
                    eth_type=ether_types.ETH_TYPE_IP,
                    ip_proto=0x01,  # icmp
                )
                actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
                self.add_flow(datapath, 1, match, actions)
                self._send_package(msg, datapath, in_port, actions)
                #self.logger.info("OTHER: %s ==> %s", dpid, dst)

        elif dpid in self.upper_tcp1_topology and (pkt.get_protocol(tcp.tcp) and pkt.get_protocol(tcp.tcp).dst_port == self.TCP1_port):

                out_port = self.upper_tcp1_topology[dpid][dst]
                print(str(bcolors.OKBLUE)+ "upper TCP1:" + str(dpid) + " ==> " + str(dst) + str(bcolors.ENDC) + " NEXT: " + str(out_port))
                self.logger.info("+++++++++++++++++++++++++++++++++")

                match = datapath.ofproto_parser.OFPMatch(
                    in_port=in_port,
                    eth_dst=dst,
                    eth_src=src,
                    eth_type=ether_types.ETH_TYPE_IP,
                    ip_proto=0x06,  # tcp
                    tcp_dst=self.TCP1_port
                )
                actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
                self.add_flow(datapath, 1, match, actions)
                self._send_package(msg, datapath, in_port, actions)

        elif dpid in self.lower_tcp2_topology and (pkt.get_protocol(tcp.tcp) and pkt.get_protocol(tcp.tcp).dst_port == self.TCP2_port):

                out_port = self.lower_tcp2_topology[dpid][dst]
                print(str(bcolors.OKBLUE)+ "lower TCP2:" + str(dpid) + " ==> " + str(dst) + str(bcolors.ENDC) + " NEXT: " + str(out_port))
                self.logger.info("+++++++++++++++++++++++++++++++++")

                match = datapath.ofproto_parser.OFPMatch(
                    in_port=in_port,
                    eth_dst=dst,
                    eth_src=src,
                    eth_type=ether_types.ETH_TYPE_IP,
                    ip_proto=0x06,  # tcp
                    tcp_dst=self.TCP2_port
                )
                actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
                self.add_flow(datapath, 1, match, actions)
                self._send_package(msg, datapath, in_port, actions)
                       

        elif dpid not in self.end_swtiches:
            out_port = ofproto.OFPP_FLOOD
            actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
            match = datapath.ofproto_parser.OFPMatch(in_port=in_port)
            self.add_flow(datapath, 1, match, actions)
            self._send_package(msg, datapath, in_port, actions)
            
        
