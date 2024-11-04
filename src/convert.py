import scapy
from scapy.all import rdpcap
#scapy outputs messy data and raw hex so I just get rid of all that stuff and format it nicely to write to the text file in convert
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

#use scapy to read the PCAP and write it to a file.
def convert(filepath):
    import os

    #Convert pcap to txt file
    base_filename = os.path.basename(filepath)
    split_filename = os.path.splitext(base_filename)
    pcap_info = split_filename[0] + '.txt'

    while(os.path.exists(filepath) == False or filepath.endswith('pcapng') == False or filepath.endswith('pcap')):
        filepath = input("Invalid file. What file would you like to load? Please input type of .pcapng")

    capture = rdpcap(filepath)

    #after the data has been extracted, format it, and write it to the file for this PCAP
    with open(pcap_info, 'a+') as txt_file:
        packet_num = 1
        for packet in capture:
            txt_file.write(format_packet(packet, packet_num))
            txt_file.write("\n" + "-" * 40 + "\n")
            packet_num += 1

    #return the opened txt file
    return txt_file