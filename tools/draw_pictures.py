from langchain_core.tools import tool
import requests
import os
import scapy
from scapy.all import rdpcap, IP, Ether
from typing import List
from src.db_config import fetch_query, execute_query, create_connection

@tool
def draw_pictures(group_id: int) -> List[str]:
    """
    Tool to draw a diagram of the MAC Addresses on a network
    and how they interact
    """

    connection = create_connection()
    if connection:
        select_query = "SELECT mac_address from pcap_groups WHERE group_id=%s"
        mac_result = fetch_query(connection, select_query, (group_id,))
        macs = mac_result[0][0]


    print("MAC ADDRESSES", macs)

    return macs


"""
Next up, we make a new LangGraph with no tools. We hand it all the info about this group of packet traces
by fetching the macs, ips, subnets, tcp_sessions from the database and using the graph state from the main LangGraph agent
Then we ask the new temporary graph we've made in this tool to draw a mermaid diagram based on all this info
that connects the mac addresses together (we will do this for all the other drawing tools as well but for drawing a diagram that
displays what we want it to). Then get the result of the new graph invocation. Return it as a string. The main agent will
print it out
"""


"""
UNFINISHED
"""