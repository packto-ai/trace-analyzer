import pyshark
from langchain_core.tools import tool
import asyncio
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.db_config import fetch_query, execute_query, create_connection


#@tool
def device_type(PCAP: str, MAC: str) -> str:
    """
    Tool to find if a given device, denoted by the MAC argument is a client
    device, server device, or router.
    """

    connection = create_connection()
    if connection:
        select_sql_query = """
        SELECT subnet
        FROM pcaps
        WHERE pcap_filepath = %s
        """
        output = fetch_query(connection, select_sql_query, (PCAP,))

        connection.close()

    subnet = str(output[0][0])
    mask = str(subnet.rsplit('.', 1)[0])

    # Load the pcapng file
    capture = pyshark.FileCapture(PCAP)

    #arrays to store ips to see if the mac address corresponds to one or multiple
    #if just one src, it is a client. if one dest, it is prob a server. 
    #If more than one of both, it is a router probably. 
    source_ips = []
    dest_ips = []

    for packet in capture:
        if ('eth' in packet and 'ip' in packet):
            if str(packet.eth.src) == MAC:
                if packet.ip.src not in source_ips:
                    source_ips.append(packet.ip.src)
            if str(packet.eth.dst) == MAC:
                if packet.ip.dst not in dest_ips:
                    dest_ips.append(packet.ip.dst)
    capture.close()

    if (len(source_ips) > 1 and len(dest_ips) > 1):
        return "Router"
    elif len(source_ips) == 1 and source_ips[0].rsplit('.', 1)[0] == mask:
        return "Client"
    elif len(dest_ips) == 1:
        return "Server"

    return "Unclear what type of device this is"

print(device_type("Trace.pcapng", "10:3d:1c:46:b9:46"))
print(device_type("Trace.pcapng", "4c:22:f3:bc:b7:18"))
