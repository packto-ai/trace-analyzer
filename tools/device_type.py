import pyshark
from langchain_core.tools import tool
import asyncio
import sys
import os
from typing import List
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.db_config import fetch_query, execute_query, create_connection
import scapy
from scapy.all import rdpcap, IP, TCP, Ether

@tool
def device_type(PCAPs: List[str], MAC: str) -> str:
    """
    Tool to find if a given device, denoted by the MAC argument is a client
    device, server device, or router.
    """

    placeholder_list = ', '.join(['%s'] * len(PCAPs))
    group_id = None

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

    connection = create_connection()
    if connection:
        select_sql_query = """
        SELECT subnet
        FROM pcap_groups
        WHERE group_id = %s
        """
        output = fetch_query(connection, select_sql_query, (group_id,))

        connection.close()

    subnet = str(output[0][0])
    mask = str(subnet.rsplit('.', 1)[0])




    #arrays to store ips to see if the mac address corresponds to one or multiple
    #if just one src, it is a client. if one dest, it is prob a server. 
    #If more than one of both, it is a router probably. 
    source_ips = []
    dest_ips = []

    # Load the pcapng file
    for PCAP in PCAPs:
        capture = rdpcap(PCAP)

        for packet in capture:
            if (packet.haslayer(Ether) and packet.haslayer(IP)):
                if str(packet.eth.src) == MAC:
                    if packet[IP].src not in source_ips:
                        source_ips.append(packet.ip.src)
                if str(packet[Ether].dst) == MAC:
                    if packet[IP].dst not in dest_ips:
                        dest_ips.append(packet[IP].dst)

    if (len(source_ips) > 1 and len(dest_ips) > 1):
        return "Router"
    elif len(source_ips) == 1 and source_ips[0].rsplit('.', 1)[0] == mask:
        return "Client"
    elif len(dest_ips) == 1:
        return "Server"

    return "Unclear what type of device this is"

# print(device_type("Trace.pcapng", "10:3d:1c:46:b9:46"))
# print(device_type(["Trace.pcapng", "Trace2.pcapng"], "4c:22:f3:bc:b7:18"))
