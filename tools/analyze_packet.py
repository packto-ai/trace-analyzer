from langchain_core.tools import tool
import pyshark.packet
import pyshark.packet.packet
import scapy
from scapy.all import rdpcap
from src.db_config import fetch_query, execute_query, create_connection

@tool
def analyze_packet(PCAP: str, packetnum: int) -> str:
    """
    Tool to find any information about a specific 
    packet within a trace
    """

    connection = create_connection()
    if connection:

        select_query = "SELECT init_qa FROM pcap_groups WHERE group_id=%s"
        result = fetch_query(connection, select_query, (group_id,))

        select_query = "SELECT group_path from pcap_groups WHERE group_id=%s"
        group_result = fetch_query(connection, select_query, (group_id,))
        group = group_result[0][0]

        files_in_group = [f"{group}/{filename}" for filename in os.listdir(group)]

    packet_index = packetnum - 1 #For indexing. 5th packet will be at 4th index of capture for example

    # Load the pcapng file
    capture = rdpcap(PCAP)

    #get the packet the user specified
    packet = capture[packet_index]

    packet_show = packet.show(dump=True)

    #include everything from the packet besides the raw hex
    summary = packet_show.split("###[ Raw ]###")[0].rstrip()

    return summary

