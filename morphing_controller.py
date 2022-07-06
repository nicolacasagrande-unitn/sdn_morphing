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
    COLOR_RED = '\x1b[31m'
    COLOR_GREEN = '\x1b[32m'
    COLOR_YELLOW = '\x1b[33m'
    COLOR_BLUE = '\x1b[34m'
    COLOR_MAGENTA = '\x1b[35m'
    COLOR_CYAN = '\x1b[36m'
    ENDC = '\033[0m'

#prints the path that the packet follows from the sender to the receiver 
#every switch that the packet reaches is printed in this way: 
#[<switch_number>](eth: <eth_number>)(dst: <destination_MAC>)
#the path followed by the acknowledgement packets is not printed 
def print_path(self, current_switch, out_port, dst_host, service, src_port):
    #only the packets that have a destination MAC that starts with 00 are printed, this to avoid packets sent automatically by RYU controller 
    #the packets are only printed if they do not come from the ports that we selected for the service in this way we avoid printing acknowledgement packets
    if(dst_host[0:2]=="00" and src_port != self.video and src_port != self.documents and src_port != self.messages):
        color = ""
        if(service=="ul"):
            color = bcolors.COLOR_GREEN
        elif(service=="ur"):
            color = bcolors.COLOR_YELLOW
        elif(service=="us"):
            color = bcolors.COLOR_BLUE
        elif(service=="ll"):
            color = bcolors.COLOR_MAGENTA
        elif(service=="lr"):
            color = bcolors.COLOR_CYAN
        elif(service=="ls"):
            color = bcolors.COLOR_RED

        self.logger.info(str(color)+ "[%s](eth: %s)(dst: %s) =>" + str(bcolors.ENDC),current_switch,out_port,dst_host)


class TrafficSlicing(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TrafficSlicing, self).__init__(*args, **kwargs)

        #we have selected three different services that have been assigned to three different ports
        self.video = 9999 # upper_part = ring lower_part = line 
        self.documents = 8880 # upper_part = star lower_part = ring 
        self.messages = 8888 # upper_part = line lower_part = star 

        #in the self.mac_port variable we define the rules that swithces will have to follow for all the packets regardless of their type
        self.mac_port = {
            2: {"00:00:00:00:00:01": 2},
            3: {"00:00:00:00:00:02": 2},
            4: {"00:00:00:00:00:01": 1, "00:00:00:00:00:02": 1, "00:00:00:00:00:03": 2, "00:00:00:00:00:04": 2, "00:00:00:00:00:05": 2, "00:00:00:00:00:06": 1, "00:00:00:00:00:07": 1},
            5: {"00:00:00:00:00:07": 2, "00:00:00:00:00:06": 2},
            6: {"00:00:00:00:00:01": 1, "00:00:00:00:00:02": 1, "00:00:00:00:00:03": 2, "00:00:00:00:00:04": 2, "00:00:00:00:00:05": 2, "00:00:00:00:00:06": 1, "00:00:00:00:00:07": 1},
            7: {"00:00:00:00:00:03": 2},
            8: {"00:00:00:00:00:04": 2},
            9: {"00:00:00:00:00:05": 2},
            11: {"00:00:00:00:00:07": 3, "00:00:00:00:00:06": 2}
        }
        
        #rules followed by s1 in the upper star topology
        self.s1 = {
            1: {"00:00:00:00:00:01": 1, "00:00:00:00:00:02": 2, "00:00:00:00:00:03": 3, "00:00:00:00:00:04": 3, "00:00:00:00:00:05": 3, "00:00:00:00:00:06": 4, "00:00:00:00:00:07": 4 }
        }
        
        #rules followed by s10 in the lower star topology
        self.s10 = {
            10: {"00:00:00:00:00:01": 1, "00:00:00:00:00:02": 1, "00:00:00:00:00:03": 2, "00:00:00:00:00:04": 3, "00:00:00:00:00:05": 4, "00:00:00:00:00:06": 1, "00:00:00:00:00:07": 1 }
        }
        

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

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

        #check if the switch has the destination in the self.mac_port variable
        #in that case we are in one of the external switches so we just have to send the packet 
        #in fact the external switches do not have to follow specific paths based on the packet type
        #if the destination is not in self.mac_port but the switch is external
        #the packet is sent to the central switch
        if dpid in self.mac_port:
            if dst in self.mac_port[dpid]:
                out_port = self.mac_port[dpid][dst]
            else:
                out_port = 1
            
            #if the packet has to go back to the source port the out_port is set to OFPP_IN_PORT
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
            
            
        #upper slice, documents service, star
        #in this case the packet follows the rules defined in the self.s1 variable
        elif dpid in self.s1 and (pkt.get_protocol(tcp.tcp) and (pkt.get_protocol(tcp.tcp).dst_port == self.documents or pkt.get_protocol(tcp.tcp).src_port == self.documents)):

            out_port = self.s1[dpid][dst]

            match = datapath.ofproto_parser.OFPMatch(
                in_port=in_port,
                eth_dst=dst,
                eth_src=src,
                eth_type=ether_types.ETH_TYPE_IP,
                ip_proto=0x06,  # tcp
                tcp_dst=self.documents
            )
            actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
            self.add_flow(datapath, 1, match, actions)
            self._send_package(msg, datapath, in_port, actions)
            
            print_path(self, dpid, out_port, dst, "us", pkt.get_protocol(tcp.tcp).src_port)

        #lower slice, messages service, star
        #in this case the packet follows the rules defined in the self.s10 variable
        elif dpid in self.s10 and (pkt.get_protocol(tcp.tcp) and (pkt.get_protocol(tcp.tcp).dst_port == self.messages or pkt.get_protocol(tcp.tcp).src_port == self.messages)):

            out_port = self.s10[dpid][dst]
        
            match = datapath.ofproto_parser.OFPMatch(
                in_port=in_port,
                eth_dst=dst,
                eth_src=src,
                eth_type=ether_types.ETH_TYPE_IP,
                ip_proto=0x06,  # tcp
                tcp_dst=self.messages
            )
            actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
            self.add_flow(datapath, 1, match, actions)
            self._send_package(msg, datapath, in_port, actions)

            print_path(self, dpid, out_port, dst, "ls", pkt.get_protocol(tcp.tcp).src_port)

        #upper slice, messages service, line
        elif dpid in self.s1 and (pkt.get_protocol(tcp.tcp) and (pkt.get_protocol(tcp.tcp).dst_port == self.messages or pkt.get_protocol(tcp.tcp).src_port == self.messages)):

            #real_next would be the port to choose in the star topology 
            real_next = self.s1[dpid][dst]
            src_port = in_port
            
            #the out_port in the line case is calculated based on source and destination ports
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
                tcp_dst=self.messages
            )
            actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
            self.add_flow(datapath, 1, match, actions)
            self._send_package(msg, datapath, in_port, actions)

            print_path(self, dpid, out_port, dst, "ul", pkt.get_protocol(tcp.tcp).src_port)
            

        #lower slice, documents service, ring
        elif dpid in self.s10 and (pkt.get_protocol(tcp.tcp) and (pkt.get_protocol(tcp.tcp).dst_port == self.documents or pkt.get_protocol(tcp.tcp).src_port == self.documents)):

            #the out_port in the ring case is calculated
            out_port = (in_port%4)+1
            
            match = datapath.ofproto_parser.OFPMatch(
                in_port=in_port,
                eth_dst=dst,
                eth_src=src,
                eth_type=ether_types.ETH_TYPE_IP,
                ip_proto=0x06,  # tcp
                tcp_dst=self.documents
            )
            actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
            self.add_flow(datapath, 1, match, actions)
            self._send_package(msg, datapath, in_port, actions)

            print_path(self, dpid, out_port, dst, "lr", pkt.get_protocol(tcp.tcp).src_port)
                  
                       
        #upper slice, video service, ring
        elif dpid in self.s1 and pkt.get_protocol(udp.udp) and (pkt.get_protocol(udp.udp).dst_port == self.video or pkt.get_protocol(udp.udp).src_port == self.video):
            
            #the out_port in the ring case is calculated
            out_port = (in_port%4)+1
            
            if(in_port == out_port):
                out_port = ofproto.OFPP_IN_PORT
            
            match = datapath.ofproto_parser.OFPMatch(
                in_port=in_port,
                eth_dst=dst,
                eth_src=src,
                eth_type=ether_types.ETH_TYPE_IP,
                ip_proto=0x11,  # udp
                udp_dst=self.video,
            )

            actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
            self.add_flow(datapath, 2, match, actions)
            self._send_package(msg, datapath, in_port, actions)

            print_path(self, dpid, out_port, dst, "ur", pkt.get_protocol(udp.udp).src_port)

        #lower slice, video service, line
        elif dpid in self.s10 and pkt.get_protocol(udp.udp) and (pkt.get_protocol(udp.udp).dst_port == self.video or pkt.get_protocol(udp.udp).src_port == self.video):

                #real_next would be the port to choose in the star topology
                real_next = self.s10[dpid][dst]
                src_port = in_port
            
                #the out_port in the line case is calculated based on source and destination ports
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
                    udp_dst=self.video,
                )

                actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
                self.add_flow(datapath, 2, match, actions)
                self._send_package(msg, datapath, in_port, actions)
                
                print_path(self, dpid, out_port, dst, "ll", pkt.get_protocol(udp.udp).src_port)