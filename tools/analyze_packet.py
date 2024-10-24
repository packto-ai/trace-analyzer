import pyshark
from langchain_core.tools import tool
import asyncio
import pyshark.packet
import pyshark.packet.packet
import scapy
from scapy.all import rdpcap

@tool
def analyze_packet(PCAP: str, packetnum: int) -> str:
    """
    Tool to find any information about a specific 
    packet within a trace
    """

    packet_index = packetnum - 1 #5th packet will be at 4th index of capture

    # Load the pcapng file
    capture = rdpcap(PCAP)

    packet = capture[packet_index]

    #print("HELLO", type(packet.show()))

    packet_show = packet.show(dump=True)

    print(type(packet_show))

    summary = packet_show.split("###[ Raw ]###")[0].rstrip()

    # capture.close()
    return summary

#print(analyze_packet("Trace.pcapng", 113))

