import pyshark
from langchain_core.tools import tool
import asyncio
import pyshark.packet
import pyshark.packet.packet

@tool
def analyze_packet(PCAP: str, packetnum: int) -> pyshark.packet.packet.Packet:
    """
    Tool to find any information about a specific 
    packet within a trace
    """

    packet_index = packetnum - 1 #5th packet will be at 4th index of capture

    # Load the pcapng file
    capture = pyshark.FileCapture(PCAP)

    packet = capture[packet_index]

    capture.close()
    return packet

# analyze_packet("Trace.pcapng", 7)

