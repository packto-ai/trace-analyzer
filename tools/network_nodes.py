from langchain_core.tools import tool
import requests
import os
import scapy
from scapy.all import rdpcap, IP, Ether
from typing import List
from src.db_config import fetch_query, execute_query, create_connection

@tool
def network_nodes(group_id: int) -> List[str]:
    """
    Tool to find any information about a specific 
    nodes in the network the trace was done on 
    or questions about specific MAC addresses
    or specific devices on the network.
    """

    connection = create_connection()
    if connection:

        select_query = "SELECT group_path from pcap_groups WHERE group_id=%s"
        group_result = fetch_query(connection, select_query, (group_id,))
        group = group_result[0][0]

        PCAPs = [f"{group}/{filename}" for filename in os.listdir(group)]

    #this will allow us to look up the mac addresses we get so we can actually get the device name
    mac_key = os.getenv('MACADDRESS_IO_API_KEY')

    nodes = []
    # Load the pcapng file
    for PCAP in PCAPs:
        mac_addresses = []
        capture = rdpcap(PCAP)

        #Get every unique mac_address in the network
        for packet in capture:
            if packet.haslayer(Ether):
                if (packet[Ether].src not in mac_addresses):
                    mac_addresses.append(packet[Ether].src)
                if (packet[Ether].dst not in mac_addresses):
                    mac_addresses.append(packet[Ether].dst)
        

        connection = create_connection()
        if connection:
            insert_query = """
            INSERT INTO macs (mac_address, group_id)
            VALUES(%s, %s);
            """
            execute_query(connection, insert_query, (mac_addresses, group_id))

        #for every mac address, look up the name of that device and update the nodes_dict with a mac_address to device name mapping then add that to the list
        for mac_address in mac_addresses:
            print(mac_address)
            nodes_dict = {}
            url = f"https://api.macvendors.com/{mac_address}"
            response = requests.get(url)

            nodes_dict.update({mac_address: response.text})

            nodes.append(nodes_dict)

    return nodes
"""
UNFINISHED
"""