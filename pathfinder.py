#Import modules for # DB
#import xml.etree.ElementTree as ET
import sqlite3
import re
#Collect source and destination
sourceip=''
destinationip=''
#List of Device configurations and type

####Funtions for octect and mask manipulations##########

# Python code to convert decimal to binary
# function definition
# it accepts a decimal value
# and prints the binary value
def decToBin(dec_value):
    # logic to convert decimal to binary
    # using recursion
    bin_value =''
    q=int(dec_value)
    while (q > 1):
        r=q % 2
        q=q //2
        bin_value= str(r) + bin_value

    r=q % 2
    bin_value= str(r) + bin_value
    return bin_value
#counts how many 1s in a bynary
def countMaskBit(bin):
    #counts how many 1s in a bynary mask from left to right
    lenght=len(bin)
    x=0
    count=0
    while (x < lenght):
        count=int(bin[x])+count
        x=x+1
    return count

def octectmask2bitlenmask(mask):
    #i.e 255.255.255.0  ----> /24
    mask1=octect2bin(mask)
    return str(countMaskBit(mask1))
def bitlenmask2obtectmask(mask):
    #i.e /24 ----> 255.255.255.0
    mask1=masklen2maskbin(mask)
    mask2=binIP2octect(mask1)
    return mask2
def octect2bin(mask):
# for a 255.0.0.0  will return 11111111000000000000000000000000 and so on
    bytelist=mask.split('.')
   
    binary=''
    for byte in bytelist:
        newbin=decToBin(byte)
        l=len(newbin)
        if l<8:
            i=8-l
            while i>0:
                newbin='0'+newbin
                i=i-1
            binary=binary+newbin
        else:
            binary=binary+newbin
    return binary
def masklen2maskbin(mask):
    #Transforms a  /24 in 11111111.11111111.11111111.00000000
    bit=0
    mask=int(mask)
    byte=''
    while bit<32:
        
        if bit<mask:
            byte=byte+'1'
            
        if mask<=bit:
            byte=byte+'0'
            
        bit=bit+1
    return(byte)

def binIP2octect(bin_IPv4):
    #Does the reverse as octect2bin, note that is not checking the range of the octects
    # for a  11111111000000000000000000000000  will return 255.0.0.0  and so on
        a=0
        b=0
        c=0
        d=0
        i=0
        if (len(bin_IPv4)!=32):
            print('bad octect lenght')

        else:
            while (i<8):
                a=a+int(bin_IPv4[i])*pow(2,7-i)
                b=b+int(bin_IPv4[i+8])*pow(2, 7-i)
                c=c+int(bin_IPv4[i+16])*pow(2, 7-i)
                d=d+int(bin_IPv4[i+24])*pow(2, 7-i)
                i=i+1
        octect=(str(a)+'.'+str(b)+'.'+str(c)+'.'+str(d))
        return octect
def host2subnet(ip,mask):
    #Given a host in octect and mask in octect format, returns subnet in octect and mask lenght
    maskbin=octect2bin(mask)
    ipbin=octect2bin(ip)
    len=countMaskBit(maskbin)
    subnet=''
    i=0
    while i<32:
        if i<len:
            subnet=subnet+ipbin[i]
        else:
            subnet=subnet+'0'
        i=i+1
    subnet=binIP2octect(subnet)
    returntuple=(subnet,mask)
    return returntuple

def if_in_net(host_octect, subnet_octect, subnet_mask_bitlen):
    #host/subnet in octect format, masks in mask lenght format. i.e ('10.2.34.5','10.2.34.0','/24')
    subnet_mask_octect=bitlenmask2obtectmask(subnet_mask_bitlen)
    print(subnet_mask_octect)
    print(type(subnet_mask_octect))
    
    (host_subnet,host_mask)=host2subnet(host_octect,subnet_mask_octect)
    
    print(host_subnet)
    print(type(host_subnet))
    if host_subnet == subnet_octect:
        return True
    else:
        return False
    
#########Functions for extraction of information from configuration #########

def extract_route_static(device,config,type,routedomain):
    #re imported in main program
    #This function assumes that the device is in the table Devices
    #This will return always a tuple like: (subnet[0],mask[0],nexthop[0],device)
    fh=open(config)
    print('Reading static routes from: '+type+' '+device+'\n')
    administrative_distance=1
    if type=='ASA':
        #Code for ASA follows
            for line in fh:
                if line.startswith('hostname'):
                    x=line.split()
                    
                if line.startswith('route'):
                    x=line.split()
                    IPs= re.findall('[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+',line)
                    subnet=IPs[0]
                    mask=IPs[1]
                    if len(IPs)<3:
                        #In same cases the route nexthop is not an IP but a name , for
                        #Instance:route INTERFACE_NAME SUBNET_IP MASK_IP NAME_IP 1
                        #Where NAME_IN_CONFIG will defined in config: name IP NAME_IP
                        #In this cases the line route len will < 3, and it and nexthop missing
                        #To find the IP of NAME_IP
                        nfh=open(config)
                        for line2 in nfh:
                            #Looking for the NAME_IP to add NEXT_HOP
                            if line2.startswith('name '):
                                
                                IP_NAME=re.findall('name\s[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+\s(.+)',line2)
                                y=line2.split()
                                
                                if IP_NAME[0]==x[4]:
                                    
                                    nexthop=y[1]
                                    

                    else:
                        nexthop=IPs[2]

                    maskbin=octect2bin(mask)
                    mask=countMaskBit(maskbin)
                    add_route(subnet,mask,nexthop,administrative_distance,device)
                    #route=(subnet,mask,nexthop)
                else:
                    continue
        #Insert in the database
    if type=='JUNIPER':
        #Code for Juniper follows
        for line in fh:
            if line.startswith('set routing-options static route'):
                x=line.split()
                if x[4]=='<REMOVED>':
                    continue
                subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)[/]',x[4])
                mask=re.findall('/([0-9]+)',x[4])
                nexthop=x[6]
                
                #route=(subnet[0],mask[0],nexthop)
                add_route(subnet[0],mask[0],nexthop,administrative_distance,device)

    if type=='F5':
        #Code for F5 follows
        #Inizialize counter
        counter=0
        for line in fh:
            if counter==2:
                x=line.split()
                #Chose route depending on route domain in F5
                if routedomain=='default':
                    subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)/',x[1])
                    mask=re.findall('[.][0-9]+/([0-9]+)',x[1])
                    if re.search('default$',x[1]):
                        subnet=['0.0.0.0']
                        mask=['0']

                if routedomain=='1':
                    subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%1',x[1])
                    mask=re.findall('%1/([0-9]+)',x[1])
                    if re.search('default\%1',x[1]):
                        subnet=['0.0.0.0']
                        mask=['0']
                if routedomain=='2':
                    subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%2',x[1])
                    mask=re.findall('%2/([0-9]+)',x[1])
                    if re.search('default\%2',x[1]):
                        subnet=['0.0.0.0']
                        mask=['0']
                if routedomain=='3':
                    subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%3',x[1])
                    mask=re.findall('%3/([0-9]+)',x[1])
                    if re.search('default\%3',x[1]):
                        subnet=['0.0.0.0']
                        mask=['0']
                if routedomain=='4':
                    subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%4',x[1])
                    mask=re.findall('%4/([0-9]+)',x[1])
                    if re.search('default\%4',x[1]):
                        subnet=['0.0.0.0']
                        mask=['0']
                if routedomain=='5':
                    subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%5',x[1])
                    mask=re.findall('%5/([0-9]+)',x[1])
                    if re.search('default\%5',x[1]):
                        subnet=['0.0.0.0']
                        mask=['0']
                if routedomain=='6':
                    subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%6',x[1])
                    mask=re.findall('%6/([0-9]+)',x[1])
                    if re.search('default\%6',x[1]):
                        subnet=['0.0.0.0']
                        mask=['0']
                if len(subnet)>>0:
                    #subnet and mask are type lst
                    route=(subnet[0],mask[0],nexthop[0])
                    add_route(subnet[0],mask[0],nexthop[0],administrative_distance,device)
                    subnet=[]
                    mask=[]

                counter=0
            if counter==1:
                #nexthop are type string
                x=line.split()
                nexthop=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)',x[1])
                counter=2
            if line.startswith('net route '):
                    counter=1
                    
            else:
                continue
    if type=='Cisco_IOS':
        #Code for Cisco IOS follows
            for line in fh:
                if line.startswith('ip route'):
                    #Searching for this pattern 'ip route 10.159.92.6 255.255.255.255 10.158.0.89'
                    x=line.split()
                    IPs= re.findall('[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+',line)

                    if len(IPs)<3:
                        #In same cases the route nexthop is not an IP but an interface ,so need to add interface
                        nexthop=(x[4])
                    else:
                        nexthop=IPs[2]

                    mask=IPs[1]
                    subnet=IPs[0]
                    maskbin=octect2bin(mask)
                    mask=countMaskBit(maskbin)
                    #Insert in the database
                    add_route(subnet,mask,nexthop,administrative_distance,device)
                    #route=(subnet,mask,nexthop,device)

def extract_route_connected(device,config,type,routedomain):
    administrative_distance=0
    fh=open(config)
    print('Reading connected routes from: '+type+' '+device+'\n')
    if type=='ASA':
    #Code for ASA follows
    #How an engineer does it, it looks at the configuration, looking for interface commands, then under
    #the command, it looks for ip address  and mask, and also for ip address and mask secondary.
    #After that it just calculates the subnets for each ip,mask
        inside_int=False
        enabled_int=True
        Addlst=list()
        IPlst=list()
        Masklst=list()
        Intlst=list()
        for line in fh:
            if line.startswith('interface'):
                inside_int=True
                enabled_int=True
                interface=re.findall('interface (\S+)',line)
            if inside_int==True:
                #Extract all the IPs, including secondary
                if line.startswith(' ip address'):
                    Address= re.findall('[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+',line)
                    IP=Address[0]
                    #Mask=octectmask2bitlenmask(Address[1])
                    Mask=Address[1]
                    Int=interface[0]
                    Addlst.append(IP)
                    Masklst.append(Mask)
                    Intlst.append(Int)

                if line.startswith(' shutdown'):
                    #Detects if interface is shutdown
                    enabled_int=False
                if ((inside_int==True) and line.startswith('!')==True):
                    #If reaches end of line ,resets inside_int flag
                    inside_int=False
                    if enabled_int==True:
                        #If interface is not shutdown
                        x=len(Addlst)
                        i=0
                        while i<x:
                            subnettuple=host2subnet(Addlst[i],Masklst[i])
                            add_route(subnettuple[0],subnettuple[1],Intlst[0],administrative_distance,device)

                            i=i+1
                        Addlst=list()
                        IPlst=list()
                        Masklst=list()
                        Intlst=list()    
    if type=='JUNIPER':
        #Code for Juniper follows
        for line in fh:
            if line.startswith('set interfaces '):
                
                x=line.split()
                subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)[/]',line)
                if len(subnet)>0:
                    mask=re.findall('/([0-9]+)',line)
                    interface=x[2]+' '+x[3]+' '+x[4]
                    
                    maskbin=masklen2maskbin(mask[0])
                    mask=binIP2octect(maskbin)
                    subnettuple=host2subnet(subnet[0],mask)
                    
                    mask1=octectmask2bitlenmask(mask)
                    #add_route(subnettuple[0],subnettuple[1],interface,administrative_distance,device)
                    add_route(subnettuple[0],mask1,interface,administrative_distance,device)
                    subnet=''
                else:
                    continue

    if type=='F5':
        inside_int=False
        enabled_int=True
        for line in fh:
            if line.startswith('net self'):
                interface=re.findall('/Common/(\S+)',line)
                inside_int=True
            if inside_int==True:
                #Extract all the IPs, including secondary
                if line.startswith('    address'):
                    if routedomain=='default':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)/',line)
                        mask=re.findall('[.][0-9]+/([0-9]+)',line)

                    if routedomain=='1':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%1/',line)
                        mask=re.findall('[.][0-9]+%1/([0-9]+)',line)

                    if routedomain=='2':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%2/',line)
                        mask=re.findall('[.][0-9]+%2/([0-9]+)',line)

                    if routedomain=='3':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%3/',line)
                        mask=re.findall('[.][0-9]+%3/([0-9]+)',line)

                    if routedomain=='4':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%4/',line)
                        mask=re.findall('[.][0-9]+%4/([0-9]+)',line)

                    if routedomain=='5':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%5/',line)
                        mask=re.findall('[.][0-9]+%5/([0-9]+)',line)

                    if routedomain=='6':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%6/',line)
                        mask=re.findall('[.][0-9]+%6/([0-9]+)',line)

                if ((inside_int==True) and line.startswith('}')==True):
                    #If reaches end of line ,resets inside_int flag
                    inside_int=False
                    if len(subnet)>>0:
                        maskbin=masklen2maskbin(mask[0])
                        maskoct=binIP2octect(maskbin)
                        maskoct1=octectmask2bitlenmask(maskoct)
                        subnettuple=host2subnet(subnet[0],maskoct)
                        
                        add_route(subnettuple[0],maskoct1,interface[0],administrative_distance,device)
                        subnet=[]
                        mask=[]
                        interface=[]
                    else:
                        continue

    if type=='Cisco_IOS':
        #Code for ASA follows
        #How an engineer does it, it looks at the configuration, looking for interface commands, then under
        #the command, it looks for ip address  and mask, and also for ip address and mask secondary.
        #After that it just calculates the subnets for each ip,mask
        inside_int=False
        enabled_int=True
        Addlst=list()
        IPlst=list()
        Masklst=list()
        for line in fh:
            if line.startswith('interface'):
                line_interface=line.split()
                interface=line_interface[1]
                inside_int=True
                enabled_int=True
            if inside_int==True:
                #Extract all the IPs, including secondary
                if line.startswith(' ip address'):
                    Address= re.findall('[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+',line)
                    IP=Address[0]
                    Mask=Address[1]
                    Addlst.append(IP)
                    Masklst.append(Mask)

                if line.startswith(' shutdown'):
                    #Detects if interface is shutdown
                    enabled_int=False
                if ((inside_int==True) and line.startswith('!')==True):
                    #If reaches end of line ,resets inside_int flag
                    inside_int=False
                    if enabled_int==True:
                        #If interface is not shutdown
                        x=len(Addlst)
                        i=0
                        while i<x:
                            subnet=host2subnet(Addlst[i],Masklst[i])
                            mask1=octectmask2bitlenmask(subnet[1])
                            add_route(subnet[0],mask1,interface,administrative_distance,device)
                            i=i+1
                        Addlst=list()
                        IPlst=list()
                        Masklst=list()

def extract_interface(device,config,type,routedomain):
    #administrative_distance=0
    fh=open(config)
    print('Reading interfaces from: '+type+' '+device+'\n')
    if type=='ASA':
    #Code for ASA follows
    #How an engineer does it, it looks at the configuration, looking for interface commands, if it finds it
    #records the interface name, then under the interface , it looks for ip address  and mask,
    # and also for ip address and mask secondary.in the case of
    #ASA the name if, zone, 
        inside_int=False
        enabled_int=True
        Addlst=list()
        IPlst=list()
        Masklst=list()
        Intlst=list()
        zone=''
        for line in fh:
            if line.startswith('interface'):
                inside_int=True
                enabled_int=True
                interface=re.findall('interface (\S+)',line)
            if inside_int==True:
                #Extract all the IPs, including secondary
                if line.startswith(' ip address'):
                    Address= re.findall('[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+',line)
                    IP=Address[0]
                    Mask=octectmask2bitlenmask(Address[1])
                    Int=interface[0]
                    Addlst.append(IP)
                    Masklst.append(Mask)
                    Intlst.append(Int)
                    ip_address=''
                    ip_mask=''
                if line.startswith(' nameif'):
                    zoneline=line.split()
                    nameif=zoneline[1]
                if line.startswith(' shutdown'):
                    #Detects if interface is shutdown
                    enabled_int=False
                if ((inside_int==True) and line.startswith('!')==True):
                    #If reaches end of line ,resets inside_int flag
                    
                    inside_int=False
                    if enabled_int==True:
                        #If interface is not shutdown
                        x=len(Addlst)
                        i=0
                        address=''
                        while i<x:
                            ip_address= ip_address+' '+Addlst[i]
                            ip_mask= ip_mask+' '+Masklst[i]
                            i=i+1
                        add_interface(interface[0],device,ip_address,ip_mask,nameif,zone)
                        Addlst=list()
                        IPlst=list()
                        Masklst=list()
                        Intlst=list()
                        address=''
    if type=='JUNIPER':
        #Code for Juniper follows
        add_interface_arguments=list()
        interface_zone_and_names=list()
        for line in fh:
            if line.startswith('set interfaces '):
                x=line.split()
                subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)[/]',line)
                if len(subnet)>0:
                    mask=re.findall('/([0-9]+)',line)
                    interface=x[2]+'.'+x[4]
                    maskbin=masklen2maskbin(mask[0])
                    nameif='n/a'
                    zone='n/a'
                    add_interface_arguments.append([interface,device,subnet[0],mask[0],nameif,zone])
                    #Zone will be added latter on
                    #GigabitEthernet0/7 572118  10.159.0.1  25 nameif,zone
                    #add_interface(interface,device,subnet[0],mask[0],nameif,zone)

            if line.startswith('set security zones security-zone'):
                x=line.split()
                
                #Select this kind of lines only: set security zones security-zone FW_BACKEND_SRV interfaces reth1.300
                if (len(x)>6) and (x[5]=='interfaces'):
                    interface_zone_and_names.append([x[4],x[6]])
                else:
                    continue
              
        print(add_interface_arguments)
        print(interface_zone_and_names)
        #(interface,device,subnet[0],mask[0],nameif,zone)
        for argument in add_interface_arguments:
            for zone_and_name in interface_zone_and_names:
                #Check if it finds the same interface name
                if argument[0] == zone_and_name[1]:
                    #Assigns the zone to the zone field in argument
                    argument[5]=zone_and_name[0]
                    
        for argument in add_interface_arguments:
            add_interface(argument[0],argument[1],argument[2],argument[3],argument[4],argument[5])
            
    if type=='F5':
        inside_int=False
        enabled_int=True
        for line in fh:
            if line.startswith('net self'):
                interface=re.findall('/Common/(\S+)',line)
                inside_int=True
            if inside_int==True:
                #Extract all the IPs, including secondary
                if line.startswith('    address'):
                    if routedomain=='default':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)/',line)
                        mask=re.findall('[.][0-9]+/([0-9]+)',line)

                    if routedomain=='1':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%1/',line)
                        mask=re.findall('[.][0-9]+%1/([0-9]+)',line)

                    if routedomain=='2':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%2/',line)
                        mask=re.findall('[.][0-9]+%2/([0-9]+)',line)

                    if routedomain=='3':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%3/',line)
                        mask=re.findall('[.][0-9]+%3/([0-9]+)',line)

                    if routedomain=='4':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%4/',line)
                        mask=re.findall('[.][0-9]+%4/([0-9]+)',line)

                    if routedomain=='5':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%5/',line)
                        mask=re.findall('[.][0-9]+%5/([0-9]+)',line)

                    if routedomain=='6':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%6/',line)
                        mask=re.findall('[.][0-9]+%6/([0-9]+)',line)

                if ((inside_int==True) and line.startswith('}')==True):
                    #If reaches end of line ,resets inside_int flag
                    inside_int=False
                    if len(subnet)>>0:
                        maskbin=masklen2maskbin(mask[0])
                        maskoct=binIP2octect(maskbin)
                        maskoct1=octectmask2bitlenmask(maskoct)
                        subnettuple=host2subnet(subnet[0],maskoct)
                     #   add_route(subnettuple[0],maskoct1,interface[0],administrative_distance,device)
                        subnet=[]
                        mask=[]
                        interface=[]
                    else:
                        continue

    if type=='Cisco_IOS':
        #Code for ASA follows
        #How an engineer does it, it looks at the configuration, looking for interface commands, then under
        #the command, it looks for ip address  and mask, and also for ip address and mask secondary.
        #After that it just calculates the subnets for each ip,mask
        inside_int=False
        enabled_int=True
        Addlst=list()
        IPlst=list()
        Masklst=list()
        for line in fh:
            if line.startswith('interface'):
                line_interface=line.split()
                interface=line_interface[1]
                inside_int=True
                enabled_int=True
            if inside_int==True:
                #Extract all the IPs, including secondary
                if line.startswith(' ip address'):
                    Address= re.findall('[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+',line)
                    IP=Address[0]
                    Mask=Address[1]
                    Addlst.append(IP)
                    Masklst.append(Mask)

                if line.startswith(' shutdown'):
                    #Detects if interface is shutdown
                    enabled_int=False
                if ((inside_int==True) and line.startswith('!')==True):
                    #If reaches end of line ,resets inside_int flag
                    inside_int=False
                    if enabled_int==True:
                        #If interface is not shutdown
                        x=len(Addlst)
                        i=0
                        while i<x:
                            subnet=host2subnet(Addlst[i],Masklst[i])
                            mask1=octectmask2bitlenmask(subnet[1])
                            #add_route(subnet[0],mask1,interface,administrative_distance,device)
                            i=i+1
                        Addlst=list()
                        IPlst=list()
                        Masklst=list()


############Functions to manipulate the database###############

def add_interface(name,device,ip_address,ip_mask,nameif,zone):
    #Receives and string like: (GigabitEthernet0/7 572118  10.159.0.1  25 nameif )
    mask=bitlenmask2obtectmask(ip_mask)
    subnet=host2subnet(ip_address,mask)
    subnet_id=get_subnet_id(subnet[0])
    device_id=get_device_id(device)
    conn = sqlite3.connect('configdb.sqlite')
    cur = conn.cursor()
    #insert route in Routes
    cur.execute('INSERT INTO Interfaces (name,device_id,subnet_id,ip_address,ip_mask,nameif,zone) VALUES (?,?,?,?,?,?,?)',(name,device_id,subnet_id,ip_address,ip_mask,nameif,zone))
    conn.commit()
def add_device(hostname,configfile,maker):
    conn = sqlite3.connect('configdb.sqlite')
    cur = conn.cursor()
    #add device in Devices
    cur.execute('INSERT INTO Devices (hostname,configfile,maker) VALUES ( ?,?,? )', (hostname,configfile,maker))
    print((hostname,configfile,maker))
    conn.commit()

def add_subnet(name,subnet,mask):
    #Returns the subnet_id of a subnet in the table Subnets
    conn = sqlite3.connect('configdb.sqlite')
    cur = conn.cursor()
    #insert subnet in Subnets
    cur.execute('INSERT OR IGNORE INTO Subnets (name,subnet,mask) VALUES (?,?,?)' , (name,subnet,mask))
    conn.commit()

def add_route(subnet,mask,nexthop,administrative_distance,device_id):
    #It always makes sure that the subnet exist by calling add_subnet() first
    add_subnet(subnet,subnet,mask)
    subnet_id=get_subnet_id(subnet)
    conn = sqlite3.connect('configdb.sqlite')
    cur = conn.cursor()
    #insert route in Routes
    cur.execute('INSERT INTO Routes (subnet_id,nexthop,administrative_distance,device_id) VALUES (?,?,?,?)',(subnet_id,nexthop,administrative_distance,device_id))
    conn.commit()

def get_subnet_id(net):
    #Returns the subnet_id of a subnet in the table Subnets
    conn = sqlite3.connect('configdb.sqlite')
    cur = conn.cursor()
    #insert subnet in Subnets
    cur.execute('SELECT id FROM Subnets WHERE subnet = ?',(net,))
    subnet_id=cur.fetchone()
    conn.commit()
    return subnet_id[0]

def get_device_id(device):
    #Returns the device_id of a subnet in the table Subnets
    conn = sqlite3.connect('configdb.sqlite')
    cur = conn.cursor()
    #insert subnet in Subnets
    cur.execute('SELECT id FROM Devices WHERE hostname = ?',(device,))
    device_id=cur.fetchone()
    conn.commit()
    return int(device_id[0])
    
#Main program starts, this program will populate the database tables that will be used by the querier module
#to find what devices are in the path between modules

########Definition of devices###############

#Device_list=[('572120','572120_network.txt','ASA','default'),('572118','572118_network.txt','ASA','default'),('825183','825183_network.txt','JUNIPER','default'),('572126default','572126_network.txt','F5','default'),('572126%1','572126_network.txt','F5','1'),('572126%2','572126_network.txt','F5','2'),('572126%3','572126_network.txt','F5','3'),('572126%4','572126_network.txt','F5','4'),('572126%5','572126_network.txt','F5','5'),('572126%6','572126_network.txt','F5','6'),('RS_LON5_705883_CS','RS_LON5_705883_CS.txt','Cisco_IOS','default'),('GBLon03-CSW01','GBLon03-CSW01.txt','Cisco_IOS','default'),('ips01-dc3-asa-1-pri','ips01-dc3-asa-1-pri.txt','ASA','default')]
Device_list=[('825183','825183_network.txt','JUNIPER','default'),('572118','572118_network.txt','ASA','default')]

#In the future source and destination protocols to be added
#Another module would extract the routes, firewalls and next hops and store
#in a database
#
#################Create database ################


conn = sqlite3.connect('configdb.sqlite')
cur = conn.cursor()

# Make some fresh tables using executescript()
# Create Tables for Devices, Interfaces, Routes,Subnets
cur.executescript('''
DROP TABLE IF EXISTS Devices;
DROP TABLE IF EXISTS Interfaces;
DROP TABLE IF EXISTS Subnets;
DROP TABLE IF EXISTS Routes;

CREATE TABLE Devices (
    id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    hostname  TEXT UNIQUE,
    configfile TEXT,
    maker   TEXT
);

CREATE TABLE Interfaces (
    id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    name   TEXT ,
    device_id INTEGER,
    subnet_id INTEGER,
    ip_address TEXT,
    ip_mask TEXT,
    nameif TEXT,
    zone TEXT
);

CREATE TABLE Subnets (
    id  INTEGER NOT NULL PRIMARY KEY
        AUTOINCREMENT UNIQUE,
    name TEXT  ,
    subnet  INTEGER,
    mask  INTEGER,
    UNIQUE (subnet,mask)  
);
CREATE TABLE Routes (
    id  INTEGER NOT NULL PRIMARY KEY
        AUTOINCREMENT UNIQUE,
    subnet_id TEXT,
    nexthop TEXT,
    administrative_distance INTEGER,
    device_id INTEGER
    );
''')

#########Extraction of information in table########

for deviceinfo in Device_list:
    #This is how the tuples in device list look like ('572120','572120.txt','ASA','default')
    add_device(deviceinfo[0],deviceinfo[1],deviceinfo[2])

conn.commit()


#Device info looks like: ('572120','572120_network.txt','ASA','default')
for deviceinfo in Device_list:
    extract_route_static(deviceinfo[0],deviceinfo[1],deviceinfo[2],deviceinfo[3])
for deviceinfo in Device_list:
    extract_route_connected(deviceinfo[0],deviceinfo[1],deviceinfo[2],deviceinfo[3])
for deviceinfo in Device_list:
    extract_interface(deviceinfo[0],deviceinfo[1],deviceinfo[2],deviceinfo[3])
#Test function


#Need to standarize the output of all the functions-Done
#Need to create the function for the Cisco Switch as well-Done
#I tested the loop and no errors in the extract_route_static funtion, need to add the database commands to-Done, there is a dependency in
#having subnets ID , in order to progress, need to add subnets to the subnets table as i create routes.-Done
#Populate the table with routes, with a test subnet_id. -Done
#Create scripts to extract connected subnets from devices and add to tables-Done
    #Done for Cisco Switch
    #Pending F5
    #Pending Juniper
    #Pending ASA
# There was an issue with duplicated subnets, due duplicated F5 interfaces. fixed with insert 
# Ignore and with making in subnet, the subnet and mask unique.-Done
# There was an addition of a administrative_distance in the route table, to deal with the routes added when
# extracting subnets vs extracting interfaces-Done
#Found error in mask of an output , done on 1st February, version 3-Done
#Create funtions to add_interface -Done
#using the subnet, and not the mask, issues will happen when subnet1 = subnet2, but they have different mask
#For instance 10.2.3.0 255.255.255.0 and 10.2.3.0 255.255.255.128 -Done
#Next task: Create funcion to extract_interfaces()-Done
##Issues with extraction. 1. Juniper and F5 not showing in the interface table -Fixed   2. in Route table the device id, is not the table id from
#the device table.

#Flow:(source ip,gateway,protocol,source port,destination_ip,destination_port)
#Function to tell if two host are in same subnet , if_in_net -Done

#Check if source_ip and gateway are in same subnet.
#For a source_ip make a loop in all the subnets and will find the subnet.

#Once it finds the subnet, will find what interfaces belong to this subnet, then will give the device names

#If there are more than two devices , it will answer for the default gateway of the source host, if not, will assume that
#Traffic goes via the only device in the subnet

#Will then lookup in the routing table of the Device to find next hop

#Create function to relate subnet with ip and ip with interface.
#Create function to lookup routes
#The create program to calculate the path, perhaps i should just populate a permanent table with the paths.

#Version control.
#v4 created the function add_interface

#Know issues
#An issue to fix is that the subnet and mask are unique, at the moment the get_subnet_id function is only


#Improvement list
#-Add in juniper the description to nameif
#Add in ASA to the zone, the access-list name applied to the interface
#Add in IOS to the zone, the access-list name applied to the interface
