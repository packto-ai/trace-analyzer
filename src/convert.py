import pyshark
def format_packet(packet):
    packet_info = f"Packet Number: {packet.number}\n"
    packet_info += f"Length: {packet.length}\n"

    for layer in packet.layers:
        packet_info += f"Layer: {layer.layer_name}\n"
        for field in layer.field_names:
            value = getattr(layer, field, None)
            packet_info += f"   {field}: {value}\n" if value is not None else f"    {field}: Not Available\n"

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

    capture = pyshark.FileCapture(filepath)

    with open(pcap_info, 'a+') as txt_file:
        for packet in capture:
            txt_file.write(format_packet(packet))
            txt_file.write("\n" + "-" * 40 + "\n")

    #return the opened csv file to PingInterpeter so it can use the LLM to analyze it
    return txt_file

#convert("Trace.pcapng")