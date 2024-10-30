import pyshark
from langchain_core.tools import tool
import asyncio
from typing import List
import scapy
from scapy.all import rdpcap, IP, TCP

@tool
def tcp_session(PCAPs: List[str]) -> str:
    """
    Tool to find the TCP sessions in a trace or group of traces
    """
    sessions = []

    for PCAP in PCAPs:
    # Load the pcapng file
        capture = rdpcap(PCAP)
        for packet in capture:
            #If a packet uses TCP protocol, it has a TCP session
            if (isinstance(packet.lastlayer(), TCP) and packet.haslayer(IP)):
                session_tuple = (packet[IP].src, packet[TCP].sport, packet[IP].dst, packet[TCP].dport) #these are all the important pieces of info for a tcp session
                if session_tuple not in sessions:
                    sessions.append(session_tuple)

    #join each tuple into a comma-separated string and return it
    return ', '.join(str(session) for session in sessions)