#!/usr/bin/python3

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.link import TCLink


class NetworkSlicingTopo(Topo):
    def __init__(self):
        # Initialize topology
        Topo.__init__(self)

        # Create template host, switch, and link
        host_config = dict(inNamespace=True)
        switch_config = dict(bw=20)

        # Create switch nodes
        for i in range(11):
            sconfig = {"dpid": "%016x" % (i + 1)}
            self.addSwitch("s%d" % (i + 1), **sconfig)

        # Create host nodes
        for i in range(7):
            self.addHost("h%d" % (i + 1), **host_config)
        
        # Add switch and host links in a specific order

        #Upper slice
        self.addLink("s1", "s2", **switch_config)
        self.addLink("s1", "s3", **switch_config)
        self.addLink("s1", "s4", **switch_config)
        self.addLink("s1", "s5", **switch_config)
        self.addLink("s2", "h1", **host_config)
        self.addLink("s3", "h2", **host_config)
        self.addLink("s5", "s11", **switch_config)
        self.addLink("s5", "h6", **host_config)
        self.addLink("s5", "h7", **host_config)

        #Middle connection
        self.addLink("s4", "s6", **switch_config)

        #Lower slice
        self.addLink("s10", "s6", **switch_config)
        self.addLink("s10", "s7", **switch_config)
        self.addLink("s10", "s8", **switch_config)
        self.addLink("s10", "s9", **switch_config)
        self.addLink("s9", "h5", **host_config)
        self.addLink("s7", "h3", **host_config)
        self.addLink("s8", "h4", **host_config)
        
topos = {"networkslicingtopo": (lambda: NetworkSlicingTopo())}

if __name__ == "__main__":
    topo = NetworkSlicingTopo()
    net = Mininet(
        topo=topo,
        switch=OVSKernelSwitch,
        build=False,
        autoSetMacs=True,
        autoStaticArp=True,
        link=TCLink,
    )
    controller = RemoteController("c1", ip="127.0.0.1", port=6633)
    net.addController(controller)
    net.build()
    net.start()
    CLI(net)
    net.stop()
