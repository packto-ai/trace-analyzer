from langchain_core.tools import tool
from typing import List
import scapy
from scapy.all import rdpcap, IP, IPv6, TCP
import json
import ast

@tool
def tcp_session(PCAPs: List[str]) -> str:
    """
    Tool to find the TCP sessions in a trace or group of traces
    """

    print("PCAPS", PCAPs)

    sessions = []

    for PCAP in PCAPs:
    # Load the pcapng file
        capture = rdpcap(PCAP)
        for packet in capture:
            #If a packet uses TCP protocol, it has a TCP session
            if (packet.haslayer(TCP) and (packet.haslayer(IP) or packet.haslayer(IPv6))):
                session_tuple = None
                if (packet.haslayer(IP)):
                    session_tuple = (packet[IP].src, packet[TCP].sport, packet[IP].dst, packet[TCP].dport) #these are all the important pieces of info for a tcp session
                elif packet.haslayer(IPv6):
                    session_tuple = (packet[IPv6].src, packet[TCP].sport, packet[IPv6].dst, packet[TCP].dport) #these are all the important pieces of info for a tcp session
                if session_tuple not in sessions:
                    sessions.append(session_tuple)

    seen = set()
    unique_sessions = []

    for session in sessions:
        #for every session, sort the tuple in pairs to essentially find different permutations
        #of a tcp session so that it doesn't have duplicates
        src = (session[0], session[1])
        dest = (session[2], session[3])

        sorted_tuple = tuple(sorted([src, dest]))

        if sorted_tuple not in seen:
            seen.add(sorted_tuple)
            unique_sessions.append(session)

    #join each tuple into a comma-separated string and return it
    if (unique_sessions == []):
        return "No active TCP sessions"
    return ', '.join(str(session) for session in unique_sessions)


# print("SESSIONS", tcp_session("['uploads/tools/ipv4frags.pcap']"))