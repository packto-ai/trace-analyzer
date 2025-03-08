import pyshark
from langchain_core.tools import tool
import asyncio
import pyshark.packet
import pyshark.packet.packet
import json
import scapy
from scapy.all import rdpcap, Ether, IP
from typing import List
from src.db_config import fetch_query, execute_query, create_connection
import os

@tool
def ip_mac(group_id: int) -> list:
    """
    Tool to find the all the MAC addresses and their corresponding IP addresses on the network
    """

    connection = create_connection()
    if connection:

        select_query = "SELECT group_path from pcap_groups WHERE group_id=%s"
        group_result = fetch_query(connection, select_query, (group_id,))
        group = group_result[0][0]

        PCAPs = [f"{group}/{filename}" for filename in os.listdir(group)]

    #will store all the key-value pairs of mac: ip for every device on the network
    mappings = []
    mac_addresses = []
    for PCAP in PCAPs:
        # Load the pcapng file
        capture = rdpcap(PCAP)

        #The ether layer's src is the MAC address and the IP layer's src is the IP Address
        for packet in capture:
            mapping_dict = {}
            if (packet.haslayer(Ether) and packet.haslayer(IP)):
                mapping_dict.update({packet[Ether].src: packet[IP].src})
                mac_addresses.append(packet[Ether].src)
                if mapping_dict not in mappings:
                    mappings.append(mapping_dict)

    seen_keys = set()
    unique_mappings = []


    mac_addresses = list(dict.fromkeys(mac_addresses))
    print("MACKIE", mac_addresses)

    connection = create_connection()
    if connection:
        insert_query = """
        INSERT INTO macs (mac_address, group_id)
        VALUES(%s, %s);
        """
        execute_query(connection, insert_query, (mac_addresses, group_id))


    #get only the unique key-value pairs
    for d in mappings:
        for key in d:
            if key not in seen_keys:
                seen_keys.add(key)
                unique_mappings.append(d)
                
    return json.dumps(unique_mappings)

"""
UNFINISHED
"""