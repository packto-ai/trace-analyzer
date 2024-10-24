import scapy
from scapy.all import rdpcap
def format_packet(packet, packet_num):
    packet_info = f"Packet Number: {packet_num}\n"
    packet_info += f"Length: {len(packet)}\n"

    layer = packet
    while layer:
        packet_info += f"Layer: {layer.name}\n"
        for field in list(layer.fields.keys()):
            value = getattr(layer, field, None)
            packet_info += f"   {field}: {value}\n" if value is not None else f"    {field}: Not Available\n"
        layer = layer.payload if hasattr(layer, 'payload') else None

    packet_info += "\n"

    return packet_info

def convert(filepath):
    import os

    #Convert pcap to CSV
    base_filename = os.path.basename(filepath)
    split_filename = os.path.splitext(base_filename)
    pcap_info = split_filename[0] + '.txt'

    while(os.path.exists(filepath) == False or filepath.endswith('pcapng') == False):
        filepath = input("Invalid file. What file would you like to load? Please input type of .pcapng")

    capture = rdpcap(filepath)

    with open(pcap_info, 'a+') as txt_file:
        packet_num = 1
        for packet in capture:
            txt_file.write(format_packet(packet, packet_num))
            txt_file.write("\n" + "-" * 40 + "\n")
            packet_num += 1

    #return the opened csv file to PingInterpeter so it can use the LLM to analyze it
    return txt_file

# convert("Trace.pcapng")