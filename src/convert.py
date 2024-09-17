def convert(file_path):
    import os
    from scapy.all import PcapNgReader

    #Convert pcap to CSV
    filepath = file_path
    base_filename = os.path.basename(filepath)
    split_filename = os.path.splitext(base_filename)
    csv_file = split_filename[0] + '.csv'

    while(os.path.exists(filepath) == False or filepath.endswith('pcapng') == False):
        filepath = input("Invalid file. What file would you like to load? Please input type of .pcapng")

    with open(csv_file, 'a+') as f:
        f.write("'No.','Time','Source','Destination','Protocol','Length','Info'\n")
        f.flush()

    

    #Variables to store packet info from the pcapng file
    #we will assign them using scapy
    packets = PcapNgReader(filepath) #use scapy to put all the packets in list format
    number = 0
    timestamp = 0.0
    src_ip = ''
    dest_ip = ''
    protocol = ''
    length = 0
    info = ''

    protocol_nums = {1: "ICMP", 2: "IGMP", 6: "TCP", 17: "UDP"} #dictionary to map proto output from scapy to protocol names 

    for i, packet in enumerate(packets):
        #Packet is sorted by either IP or IPv6. I'm not sure if there are others I'll check though
        if (packet.haslayer('IP')):
            number = i + 1
            ip = packet.getlayer('IP')
            timestamp = ip.time
            src_ip = ip.src
            dest_ip = ip.dst
            protocol = protocol_nums.get(ip.proto, 'N/A')
            length = len(packet.original)
            info = ip.summary()
        elif (packet.haslayer('IPv6')):
            number = i + 1
            ipv6 = packet.getlayer('IPv6')
            timestamp = ipv6.time
            src_ip = ipv6.src
            dest_ip = ipv6.dst
            protocol = protocol_nums.get(ipv6.nh, 'N/A')
            length = len(packet.original)
            info = ipv6.summary()

        with open(csv_file, 'a') as f2:
            #write it all into the new csv file we created. Thus, we can now load in a csv file which we couldn't do with pcapng
            f2.write(f"{number}, {timestamp}, {src_ip}, {dest_ip}, {protocol}, {length}, {info}\n")
            f2.flush()

    #return the opened csv file to PingInterpeter so it can use the LLM to analyze it
    return f2