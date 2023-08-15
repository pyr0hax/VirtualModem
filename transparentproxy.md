Install Squid:
Install Squid on your Linux machine using the appropriate package manager for your distribution.

Configure Squid:
Edit the Squid configuration file (/etc/squid/squid.conf) and add the following lines:

    http_port 3128 transparent
    acl to_theoldnet dstdomain .theoldnet.com
    cache_peer_access my_peer allow to_theoldnet
    cache_peer my_peer parent 1996 0 no-query originserver

Enable IP Forwarding:
Enable IP forwarding on your Linux machine to allow traffic to pass through the machine:

    sudo sysctl -w net.ipv4.ip_forward=1

Set Up iptables Rules:
Use iptables to redirect all outgoing HTTP traffic from your vintage computers to the Squid proxy:

    sudo iptables -t nat -A PREROUTING -i <interface> -p tcp --dport 80 -j REDIRECT --to-port 3128

Replace <interface> with the name of your network interface (e.g., eth0).

Restart Services:

Restart Squid and apply iptables rules:

    sudo service squid restart
    sudo iptables-save > /etc/iptables/rules.v4

Now set your machine to point to your proxy server as gateway.