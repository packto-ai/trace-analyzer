import pyshark
from langchain_core.tools import tool
import asyncio
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.db_config import fetch_query, execute_query, create_connection

@tool
def subnet(PCAP: str) -> str:
    """
    Tool to find the local subnet where the trace is taken
    """

    # Load the pcapng file
    capture = pyshark.FileCapture(PCAP)

    subnet = None

    ip_addrs = []

    try:
        for packet in capture:
            if packet.highest_layer == "ARP":
                if ('arp' in packet):
                    ip = packet.arp.src_proto_ipv4
                    ip_parts = ip.split('.')
                    ip_parts[-1] = '0'
                    subnet = '.'.join(ip_parts)
                    connection = create_connection()
                    if connection:
                        update_query = """
                        UPDATE pcaps
                        SET subnet = %s
                        WHERE pcap_filepath = %s;
                        """
                        execute_query(connection, update_query, (subnet, str(PCAP)))
                    return subnet
            if ('eth' in packet and 'ip' in packet):
                ip_addrs.append(packet.ip.src.rsplit('.', 1)[0])
                ip_addrs.append(packet.ip.dst.rsplit('.', 1)[0])
    finally:
        capture.close()

    if (all(x == ip_addrs[0] for x in ip_addrs)):
        subnet = ip_addrs[0]
    else:
        subnet_mask = max(set(ip_addrs), key=ip_addrs.count)
        subnet = f"Cannot conclusively determine subnet without you confirming the subnet mask. I suspect it is {subnet_mask}"

    connection = create_connection()
    if connection:
        update_query = """
        UPDATE pcaps
        SET subnet = %s,
        WHERE pcap_filepath = %s;
        """
        execute_query(connection, update_query, (subnet, PCAP))

    return subnet

# print(subnet("Trace.pcapng"))

