from email.policy import default
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

def print_path(self, current_switch, out_port, dst_host, service, src_port):
    if(dst_host[0:2]=="00" and src_port != self.UDP_port and src_port != self.TCP1_port and src_port != self.TCP2_port):
        color = ""
        if(service=="ul"):
            color = bcolors.OKBLUE
        elif(service=="ur"):
            color = bcolors.OKCYAN
        elif(service=="us"):
            color = bcolors.OKGREEN
        elif(service=="ll"):
            color = bcolors.WARNING
        elif(service=="lr"):
            color = bcolors.FAIL
        elif(service=="ls"):
            color = bcolors.HEADER

        self.logger.info(str(color)+ "[%s](eth: %s)(dst: %s) =>" + str(bcolors.ENDC),current_switch,out_port,dst_host)
    


class TrafficSlicing(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TrafficSlicing, self).__init__(*args, **kwargs)

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
            5: {"00:00:00:00:00:07": 2, "00:00:00:00:00:06": 2},
            4: {"00:00:00:00:00:01": 1, "00:00:00:00:00:02": 1, "00:00:00:00:00:03": 2, "00:00:00:00:00:04": 2, "00:00:00:00:00:05": 2, "00:00:00:00:00:06": 1, "00:00:00:00:00:07": 1},
            6: {"00:00:00:00:00:01": 1, "00:00:00:00:00:02": 1, "00:00:00:00:00:03": 2, "00:00:00:00:00:04": 2, "00:00:00:00:00:05": 2, "00:00:00:00:00:06": 1, "00:00:00:00:00:07": 1}
        }
        #upper, 8880, star
        self.upper_tcp1_topology = {
            1: {"00:00:00:00:00:01": 1, "00:00:00:00:00:02": 2, "00:00:00:00:00:03": 3, "00:00:00:00:00:04": 3, "00:00:00:00:00:05": 3, "00:00:00:00:00:06": 4, "00:00:00:00:00:07": 4 }
        }
        #lower, 8888, star
        self.lower_tcp2_topology = {
            10: {"00:00:00:00:00:01": 1, "00:00:00:00:00:02": 1, "00:00:00:00:00:03": 2, "00:00:00:00:00:04": 3, "00:00:00:00:00:05": 4, "00:00:00:00:00:06": 1, "00:00:00:00:00:07": 1 }
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
        res = datapath.send_msg(out)

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
        tcp_port = pkt.get_protocol(tcp.tcp)
        prot = "OTHER"
        if pkt.get_protocol(udp.udp):
            prot = "UDP"
        elif pkt.get_protocol(tcp.tcp):
            prot = "TCP"

        
       
        #controllo che lo switch sia in self.macport e la destinazione sia in self.mac_port[switch]
        if dpid in self.mac_port:
            if dst in self.mac_port[dpid]:
                out_port = self.mac_port[dpid][dst]
            else:
                out_port = 1
            
            if(in_port == out_port):
                out_port = ofproto.OFPP_IN_PORT
            
            actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
            match = datapath.ofproto_parser.OFPMatch(eth_dst=dst)
            self.add_flow(datapath, 1, match, actions)
            self._send_package(msg, datapath, in_port, actions)

            
            if(pkt.get_protocol(tcp.tcp)):
                print_path(self, dpid, out_port, dst, "", pkt.get_protocol(tcp.tcp).src_port)
            elif(pkt.get_protocol(udp.udp)):
                print_path(self, dpid, out_port, dst, "", pkt.get_protocol(udp.udp).src_port)
            
            
            

        #upper slice, tcp 8880 star
        elif dpid in self.upper_tcp1_topology and (pkt.get_protocol(tcp.tcp) and (pkt.get_protocol(tcp.tcp).dst_port == self.TCP1_port or pkt.get_protocol(tcp.tcp).src_port == self.TCP1_port)):

            out_port = self.upper_tcp1_topology[dpid][dst]

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
            
            print_path(self, dpid, out_port, dst, "us", pkt.get_protocol(tcp.tcp).src_port)

        #lower slice, tcp 8888, star
        elif dpid in self.lower_tcp2_topology and (pkt.get_protocol(tcp.tcp) and (pkt.get_protocol(tcp.tcp).dst_port == self.TCP2_port or pkt.get_protocol(tcp.tcp).src_port == self.TCP2_port)):

            out_port = self.lower_tcp2_topology[dpid][dst]
        

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

            print_path(self, dpid, out_port, dst, "ls", pkt.get_protocol(tcp.tcp).src_port)

        #upper slice, tcp 8888, line
        elif dpid in self.upper_tcp1_topology and (pkt.get_protocol(tcp.tcp) and (pkt.get_protocol(tcp.tcp).dst_port == self.TCP2_port or pkt.get_protocol(tcp.tcp).src_port == self.TCP2_port)):

            real_next = self.upper_tcp1_topology[dpid][dst]
            src_port = in_port
            
            if src_port < real_next:
                out_port = src_port+1
            else:
                out_port = src_port-1

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

            print_path(self, dpid, out_port, dst, "ul", pkt.get_protocol(tcp.tcp).src_port)
            

        #lower slice, tcp 8880 ring
        elif dpid in self.lower_tcp2_topology and (pkt.get_protocol(tcp.tcp) and (pkt.get_protocol(tcp.tcp).dst_port == self.TCP1_port or pkt.get_protocol(tcp.tcp).src_port == self.TCP1_port)):

            out_port = (in_port%4)+1


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

            print_path(self, dpid, out_port, dst, "lr", pkt.get_protocol(tcp.tcp).src_port)
                       
        #upper, udp, 9999, ring
        elif dpid in self.upper_tcp1_topology and pkt.get_protocol(udp.udp) and (pkt.get_protocol(udp.udp).dst_port == self.UDP_port or pkt.get_protocol(udp.udp).src_port == self.UDP_port):
            
            out_port = (in_port%4)+1
            
            if(in_port == out_port):
                out_port = ofproto.OFPP_IN_PORT
            
            match = datapath.ofproto_parser.OFPMatch(
                in_port=in_port,
                eth_dst=dst,
                eth_src=src,
                eth_type=ether_types.ETH_TYPE_IP,
                ip_proto=0x11,  # udp
                udp_dst=self.UDP_port,
            )

            

            actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
            self.add_flow(datapath, 2, match, actions)
            self._send_package(msg, datapath, in_port, actions)

            print_path(self, dpid, out_port, dst, "ur", pkt.get_protocol(udp.udp).src_port)

        #lower, udp, 9999, line
        elif dpid in self.lower_tcp2_topology and pkt.get_protocol(udp.udp) and (pkt.get_protocol(udp.udp).dst_port == self.UDP_port or pkt.get_protocol(udp.udp).src_port == self.UDP_port):

                real_next = self.lower_tcp2_topology[dpid][dst]
                src_port = in_port
            
                if src_port < real_next:
                    out_port = src_port+1
                else:
                    out_port = src_port-1                
                
                match = datapath.ofproto_parser.OFPMatch(
                    in_port=in_port,
                    eth_dst=dst,
                    eth_src=src,
                    eth_type=ether_types.ETH_TYPE_IP,
                    ip_proto=0x11,  # udp
                    udp_dst=self.UDP_port,
                )

                actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
                self.add_flow(datapath, 2, match, actions)
                self._send_package(msg, datapath, in_port, actions)
                
                print_path(self, dpid, out_port, dst, "ll", pkt.get_protocol(udp.udp).src_port)