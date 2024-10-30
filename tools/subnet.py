from langchain_core.tools import tool
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.db_config import fetch_query, execute_query, create_connection
from typing import List
import scapy
from scapy.all import rdpcap, ARP, IP, Ether

@tool
def subnet(PCAPs: List[str]) -> str:
    """
    Tool to find the local subnet where the trace is taken
    """

    captures = []

    # Load the pcapng file
    for PCAP in PCAPs:
        capture = rdpcap(PCAP)
        captures.append(capture)

    subnet = None

    ip_addrs = []

    placeholder_list = ', '.join(['%s'] * len(PCAPs))

    #JOINT TABLE TO QUERY ALL FILES IN A PARTICULAR SESSION
    connection = create_connection()
    if connection:
        join_query = f"""
        SELECT pcap_groups.group_id
        FROM pcaps
        JOIN pcap_groups ON pcap_groups.group_id = pcaps.group_id
        WHERE pcaps.pcap_filepath IN ({placeholder_list});
        """
        
        output = fetch_query(connection, join_query, (tuple(PCAPs,)))
        
    group_id = output[0][0]

    for capture in captures:
        for packet in capture:
            #ARP is used to map IP addresses to devices so if we can see the IP address given by an ARP protocol we can find the subnet mask
            if isinstance(packet.lastlayer(), ARP):
                if (packet.haslayer(ARP)):
                    ip = packet[ARP].psrc
                    ip_parts = ip.split('.')
                    ip_parts[-1] = '0' #we just make the last number in the IP address 0 so it is something like 192.168.1.0 because that's how a subnet is denoted
                    subnet = '.'.join(ip_parts)
                    connection = create_connection()
                    if connection:
                        update_query = """
                        UPDATE pcap_groups
                        SET subnet = %s
                        WHERE group_id = %s;
                        """
                        execute_query(connection, update_query, (subnet, group_id))
                    return subnet
            if (packet.haslayer(Ether) and packet.haslayer(IP)): #OTHERWISE, just find every IP src and destination (only the first three numbers) for every packet in every trace
                ip_addrs.append(packet[IP].src.rsplit('.', 1)[0])
                ip_addrs.append(packet[IP].dst.rsplit('.', 1)[0])

    if (all(x == ip_addrs[0] for x in ip_addrs)): #if every value is the same, then that is the subnet mask conclusively
        subnet = ip_addrs[0]
    else: #otherwise, we just pick the most common one
        subnet_mask = max(set(ip_addrs), key=ip_addrs.count)
        subnet = f"Cannot conclusively determine subnet without you confirming the subnet mask. I suspect it is {subnet_mask}"

    connection = create_connection()
    if connection:
        update_query = """
        UPDATE pcap_groups
        SET subnet = %s
        WHERE group_id = %s;
        """
        execute_query(connection, update_query, (subnet, group_id))

    return subnet
