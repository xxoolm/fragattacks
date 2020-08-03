# <div align="center">Fragmentation & Aggregation Attacks</div>

# 1. Introduction

The discovered attacks affect all Wi-Fi networks. The attacks are identical against WPA2 and WPA3, 
because WPA3 only introduced a new authentication method meaning its encryption ciphers (CCMP and GCMP)
are identical to WPA2.

Older WPA networks by default use TKIP for encryption, and the applicability of the attacks against
this cipher are discussed in the paper. To illustrate that Wi-Fi has been vulnerable since its creation,
the paper also briefly discusses the applicability of the attacks against WEP.

__USENIX Reviewers__: Our tool is based on the hostap daemon. Most of the research code is located
in the `research` directory. This repository has been updated after the paper submission with major
usability improvements (but no new research). You can inspect the code at the time of submission
by executing `git checkout db75c47`.

**A summary of the discoveries can be found in [SUMMARY.md](SUMMARY.md).**

# 2. Supported Network Cards

Only specific wireless network cards are supported. This is because some network cards may overwrite the
sequence of fragment number of injected frames, or may reorder frames of different priority, and this
interferes with the test tool (i.e. the tool might incorrectly say a device is secure although it's not).
I have confirmed that the following network cards work properly:

|      Network Card      | USB | 5GHz |        mixed mode       |      injection mode     |      hwsim mode      |
| ---------------------- | --- | ---- | ----------------------- | ----------------------- | -------------------- |
| Intel Wireless-AC 8265 | No  | Yes  | patched driver          | yes                     | _under development_  |
| Intel Wireless-AC 3160 | No  | Yes  | patched driver          | yes                     | _under development_  |
| Technoethical N150 HGA | Yes | No   | patched driver/firmware | patched driver/firmware | _under development_  |
| TP-Link TL-WN722N v1.x | Yes | No   | patched driver/firmware | patched driver/firmware | _under development_  |
| Alfa AWUS036NHA        | Yes | No   | patched driver/firmware | patched driver/firmware | _under development_  |
| Alfa AWUS036ACM        | Yes | Yes  | patched driver          | yes                     | _under development_  |
| Alfa AWUS036ACH        | Yes | Yes  | **TODO**                | **TODO**                | _under development_  |
| Netgear WN111v2        | Yes | No   | patched driver          | yes                     | _under development_  |

The three last colums signify:

1. Mixed mode: whether the network card can be used in [mixed mode](#Mixed-mode).

2. Injection mode: whether the network card can be used as a second interface to inject frames in [injection mode](#Injection-mode).

3. Hwsim mode: whether the network card can be used in the experimental [hwsim mode](#Hwsim-mode).

_Yes_ indicates the card works out-of-the-box in the given mode. _Patched driver/firmware_
means that the card is compatible when used in combination with patched drivers and/or firmware.
_No_ means this mode is not supported by the network card.

Note that USB devices can be used inside a virtual machine, and the modified drivers and/or firmware
can be installed in this virtual machine. However, I found that the usage of virtual machines can
make network cards less reliable, and I instead recommend the usage of a live CD if you cannot install
the modified drivers/firmware natively.

More details on my experience with the above devices can be found [here](#9.5.-notes-on-device-support).
Summarized:

- I recommend the use of the Technoethical N150 HGA in either injection mode or mixed mode. This deivce
  requires the use of a patched driver and firmware.

- During my tests the AWUS036ACM dongle was unreliable when connected to a USB3.0 port, but worked
  well when connected to a USB2.0 port. This behaviour may depend on your computer.

- The Intel 3160 and 8265 are supported and extensively tested. Sometimes their firmware crashed but
  a reboot makes the network card usable again. The Intel AX200 is not compatible with the test tool.

- The WN111v2 seems to work well, although I did not test it extensively.

- The driver for the AWUS036ACH is not part of the Linux kernel and requires the installation of a separate
  driver. On some Linux distributions such as Kali you can install this driver through the package manager.

If you are unable to find one of the above network cards, you can search for [alternative network cards](#Alternative-network-cards)
that have a high chance of also working. When using a network card that is not explicitly supported
I strongly recommend to first run the [injection tests](#Network-card-injection-test) before using it.

# 3. Prerequisites

The test tool was tested on Kali Linux and Ubuntu 20.04. To install the required dependencies, execute:

	# Kali Linux and Ubuntu
	sudo apt-get update
	sudo apt-get install libnl-3-dev libnl-genl-3-dev libnl-route-3-dev libssl-dev \
		libdbus-1-dev git pkg-config build-essential macchanger net-tools python3-venv \
		aircrack-ng firmware-ath9k-htc rfkill

Now clone this repository, build the tools, and configure a virtual python3 environment:

	# **TODO: replace with real HTTP unauthenticated link on release**
	git clone https://gitlab.com/aconf/wifi.git fragattack --recursive
	cd fragattack
	./build.sh
	cd research
	python3 -m venv venv
	source venv/bin/activate
	pip install wheel
	pip install -r requirements.txt

By default the above instructions only have to be executed once. However, you do have to
execute `./build.sh` again after pulling in new code using git.

# 4. Patched Drivers

Install patched drivers:

	sudo apt-get install bison flex linux-headers-$(uname -r)
	# **TODO: replace with real HTTP unauthenticated link on release instead of separate directory?**
	cd driver-backports-5.8-rc2-1
	make defconfig-wifi
	make -j 4
	sudo make install

This compiles the drivers for all network cards supported by Linux. If you only want to compile
the drivers for network cards we explicitly tested, use `make defconfig-experiments` instead.

Now install patched `ath9k_htc` firmware:

	cd research/ath9k-firmware/
	./install.sh
	# Now reboot

The `./install.sh` script assumes the `ath9k_htc` firmware images are located in the
directory `/lib/firmware/ath9k_htc`. If this is not the case on your system you have
to manually copy `htc_7010.fw` and `htc_9271.fw` to the appropriate directory.

After installing the patched drivers and firmware you must unplug your Wi-Fi dongles
and **reboot your system**. The above instructions have to be executed again if your
Linux kernel gets updated.

Note that even when your device works out of the box, I still recommend to install the modified
drivers, as this assures there are no unexpected regressions in kernel and driver code.

In case you cannot install the modified drivers/firmware natively, you can download a
**[live Ubuntu CD]()** that contains the modified drivers/firmware along with our test tool.
Alternatively, you can use a virtual machine with USB network cards, although I found that
using a virtual machine is less reliable in pratice.

# 5. Before every usage

Every time you want to use the test tool, you first have to load the virtual python environment
as root. This can be done using:

	cd research
	sudo su
	source venv/bin/activate

You should now disable Wi-Fi in your network manager so it will not interfere with the test tool.
Also make sure no other network services are causing outgoing traffic. You can assure this by
using iptables to block traffic by executing `./droptraffic.sh` (you can revert this by rebooting).
Optionally check using `sudo airmon-ng check` to see which other processing might interfere.

The test tool can test both clients and APs:

- Testing APs: **configure the AP you want to test** by editing `research/client.conf`. This is a
  standard `wpa_supplicant` configuration file, see the [hostap documentation](https://w1.fi/cgit/hostap/plain/wpa_supplicant/wpa_supplicant.conf)
  for an overview of all the options it supports.

- Testing clients: you must execute the test tool with the `--ap` parameter (see below). This
  instructs the tool into creating an AP with as name **testnetwork** and password **abcdefgh**. Connect
  to this network with the client you want to test. By default the client must request an IP
  using DHCP. To edit properties of the created AP, such as the channel it's created on, you
  can edit `research/hostapd.conf`.

# 6. Interface Modes

## 6.1. Mixed mode

This mode requires only one wireless network card, but generally requires a patched driver and/or
firmware and only specific network cards are supported. See [Patched Drivers](#Patched-Drivers) on
how to install patched drivers/firmware, and [Supported Network Cards](#Supported-Network-Cards)
for compatible network cards. Execute the test tool in this mode using:

	./fragattack wlan0 [--ap] $COMMAND

Possible values of `$COMMAND` are listed in [testing for vulnerabilities](#testing-for-vulnerabilities)
and [extended vulnerability tests](#extended-vulnerability-tests).

One advantage of this mode is that it works well when testing clients that may enter a sleep state.
Nevertheless, if possible, I recommend disabling sleep functionality of the client being tested.

## 6.2. Injection mode

This mode requires two wireless network cards: one will act as an AP or the client, and the other
one will be used to inject frames. Execute the test tool in this mode using:

	./fragattack wlan0 --inject wlan1 [--ap] $COMMAND

Here interface wlan0 will act as a legitimate client or AP, and wlan1 will be used to inject
frames. For wlan0, any card that supports normal client or AP mode on Linux can be used. For
wlan1, a card must be used that supports injection mode according to [Supported Network Cards](#Supported-Network-Cards).

When testing clients in this mode, injected frames may be sent when the client is in a sleep state.
This causes attacks to fail, so you must make sure the client will not enter a sleep state.

## 6.3. Hwsim mode

This mode is experimental and only for research purposes. See [hwsim mode details](#Hwsim-mode-details)
for more information.


# 7. Testing for Vulnerabilities

You can test devices by running the test tool as discussed in [interface modes](#interface-modes)
and replacing `$COMMAND` with one of the commands in the table blow. We assume that clients will
request an IP using DHCP (if this is not the case see [static IP configuration](#9.2.-Static-IP-Configuration)).

The tool outputs `TEST COMPLETED SUCCESSFULLY` if the device is vulnerable to the attack corresponding
to the given `$COMMAND`, and outputs `Test timed out! Retry to be sure, or manually check result` if
the device is not vulnerable. Most attacks have several slight variants represented by different
`$COMMAND` values, and verifying the result of some tests requires running tcpdump or wireshark
on the targeted device (both points are further clarified below the table).

To **verify your test setup**, the first command in the table below performs a normal ping that must
succeed. The second command sends the ping as two fragmented Wi-Fi frames, and should only fail
in the rare case that the tested device doesn't support fragmentation. In case one of these tests
is not working, follow the instructions in [network card injection test](#network-card-injection-test)
to assure your network card is properly injecting frames.

The third and fourth commands are not attacks but verify basic defragmentation behaviour of a device
and are further discussed below the table.

|             Command              | Short description
| -------------------------------- | ---------------------------------
| <div align="center">*Sanity checks*</div>
| `ping`                           | Send a normal ping.
| `ping I,E,E`                     | Send a normal fragmented ping.
| <div align="center">*Basic device behaviour*</div>
| `ping I,E,E --delay 5`           | Send a normal fragmented ping with a 5 second delay between fragments.
| `ping-frag-sep`                  | Send a normal fragmented ping with fragments separated by another frame.
| <div align="center">*A-MSDU attacks (§3)*</div>
| `ping I,E --amsdu`               | Send a ping encapsulated in a normal (non SSP protected) A-MSDU frame.
| <div align="center">*Mixed key attacks (§4)*</div>
| `ping I,F,BE,AE`                 | Inject two fragments encrypted under a different key.
| `ping I,F,BE,AE --pn-per-qos`    | Same as above, but also works if the target only accepts consecutive PNs.
| <div align="center">*Cache attacks (§5)*</div>
| `ping I,E,R,AE`                  | Inject a fragment, try triggering a reassociation, and inject second fragment.
| `ping I,E,R,E`                   | Same as above, but with a longer delay before sending the second fragment.
| `ping I,E,R,AE --full-reconnect` | Inject a fragment, deauthenticate and reconnect, then inject second fragment.
| `ping I,E,R,E --full-reconnect`  | Same as above, but with a longer delay before sending the second fragment.
| <div align="center">*Non-consecutive PNs attack (§6.2)*</div>
| `ping I,E,E --inc-pn 2`          | Send a fragmented ping with non-consecutive packet numbers.
| <div align="center">*Mixed plain/encrypt attack (§6.3)*</div>
| `ping I,E,P`                     | Send a fragmented ping: first fragment encrypted, second fragment in plaintext.
| `ping I,P,E`                     | Send a fragmented ping: first fragment in plaintext, send fragment encrypted.
| `ping I,P`                       | Send a plaintext ping.
| `ping I,P,P`                     | Send a fragmented ping: both fragments are sent in plaintext.
| `linux-plain`                    | Mixed plaintext/encrypted fragmentation attack specific to Linux.
| <div align="center">*Broadcast fragment attack (§6.7)*</div>
| `ping I,D,P --bcast-ra`          | Send ping request in 2nd plaintext broadcasted fragment after connecting.
| `ping D,BP --bcast-ra`           | Ping in 2nd plaintext broadcasted fragment during 4-way HS (check with tcpdump).
| <div align="center">*A-MSDUs EAPOL attack (§6.8)*</div>
| `eapol-amsdu BP`                 | Send A-MSDU disguised as EAPOL during handshake (check result with tcpdump).
| `eapol-amsdu I,P`                | Same as above, except the frame is injected after obtaining an IP.
| `eapol-amsdu-bad BP`             | Send malformed A-MSDU disguised as EAPOL during handshake (use tcpdump).
| `eapol-amsdu-bad I,P`            | Same as above, except the frame is injected after obtaining an IP.

## 7.1. Sanity and implementation checks

- `ping I,E,E`: This test should only fail if the tested device doesn't support fragmentation. In case
  you encounter this, it is recommended to also run this test against a device that _does_ support
  fragmentation to assure the test tool is properly injecting fragmented frames.

- `ping I,E,E --delay 5`: This test is used to check the maximum accepted delay between two fragments.
  If this test doesn't work, try it again with `--delay 1.5` or lower. For instance, Linux removes fragments
  after 2 seconds, meaning a delay of 1.8 will work while 2.2 will result in no reply. In case the maximum
  accepted delay is low, all fragments sent in other tests must be sent within this maximum accepted delay.
  Otherwise tests will trivially fail and you might conclude a device isn't vulnerable to an attack even
  though it actually is.

- `ping-frag-sep`: This tests sends a fragmented Wi-Fi frame that is seperated by an unrelated frame.
  That is, it sends the first fragment, then a (normal) unrelated Wi-Fi frame, and finally the second fragment.
  In case this test fails, the mixed key attack and cache attack will likely also fail (since they require
  sending other frames between two fragments). The only purpose of this test is to better understand the
  behaviour of a device and learn why other tests are failing.

## 7.2. A-MSDU attack tests (§3)

The test `ping I,E --amsdu` checks if an implementation supports A-MSDUs, in which case it is vulnerable to
attacks. To prevent attacks, the network must mandate the usage of SSP A-MSDUs (and drop all non-SSP A-MSDUs).
It's currently unclear how to prevent this attack in a backward-compatible manner. See Section 3 of the paper
for details.

## 7.3. Mixed key attack tests (§4)

- When running the mixed key test against an AP, the AP must be configured to regularly renew the session
  key (PTK) by executing a new 4-way handshake (e.g. every minute). The tool will display
  `Client cannot force rekey. Waiting on AP to start PTK rekey` when waiting for this PTK rekey handshake.
  Against a low number of APs, the client can also request to renew the PTK, meaning there is no
  need to configure the AP to periodically renew the key. In this case you can let the test tool request
  to renew the PTK by adding the `--rekey-req` parameter.

- Some APs cannot be configured to regularly renew the session key (PTK). Against these APs you can instead
  try to run a cache attack test. In case the AP is vulnerable to cache attacks then it is also vulnerable
  to mixed key attacks. If the AP isn't vulnerable to cache attacks then we cannot say anything about its
  susceptibility to mixed key attacks, and in that case I recommend performing a code audit instead.

- The `--pn-per-qos` parameter assures that both injected fragments have consecutive packet numbers, which
  is required for the attack to succeed against certain devices (e.g. against Linux).

- Several devices implement the 4-way handshake differently and this will impact whether these tests will
  succeed or not. In case the tests fail, it is highly recommended to also perform the mixed key attack
  tests listed in [Extended Vulnerability Tests](#8.-Extended-Vulnerability-Tests).

## 7.4. Cache attack tests (§5)

- When testing an AP, the tool sends a first fragment, then tries to _reassociate_ with the AP, and finally
  sends the second fragment. We found that not all APs properly support the reassociation process. In that
  case, add the `--full-reconnect` option as shown in the table.

- When testing a client, the tools sends a first fragment, _disassociates_ the client, and once the client
  has reconnected will send the second fragment. Ideally the client will immediately reconnect after sending
  the disassociation frame. This may require disabling all other networks in the client being tested. We also
  found that some clients don't seem to properly handle the disassocation, and in that case you can add the
  `--full-reconnect` option as shown in the table to send a deauthentication frame instead.

## 7.5. Mixed plain/encrypt attack (§6.3)

- `ping I,E,P` and `linux-plain`: if this test succeeds the resulting attacks are described in Section 6.3
  of the paper. Summarized, in combintation with the A-MSDU or cache vulnerability it can be exploited to
  inject packets. When not combined with any other vulnerabilities the impact is implementation-specific.

- `ping I,P,E`: if this test succeeds it is trivial to inject plaintext frames towards the device _if_
  fragmentation is being used by the network.

- `ping I,P,P` and `ping I,P`: if this test succeeds it is trivial to inject plaintext frames towards the
  device independent of the network configuration.

## 7.6. Broadcast fragment attack tests (§6.7)

- So far we only found that clients are vulnerable to this attack. Moreover, several clients were only
  vulnerable while they are connecting to the network (i.e. during the execution of the 4-way handshake).

- `ping D,BP --bcast-ra`: to confirm the result of this test you have to run wireshark or tcpdump on
  the victim, and monitor whether the injected ping request is received by the victim. In tcpdump you can
  use the filter `icmp` and in wireshark you can also use the filter `frame contains "test_ping_icmp"`
  to more easily detect this ping request.

- Because these tests send broadcast frames, which are not automatically retransmitted, it is recommended
  to execute this test several times. This is because background noise may prevent the tested devices from
  receiving the injected broadcast frame.

## 7.7. A-MSDUs EAPOL attack tests (§6.8)

- Several clients and APs are only vulnerable to this attack while the client is connecting to the network
  (i.e. during the execution of the 4-way handshake).

- Several implementations incorrectly process A-MSDU frames that start with a valid EAPOL header. To test
  these implementations, you have to use the `eapol-amsdu-bad` test variant. Note that if this tests succeeds,
  the impact of the attack is identical to implementations that correctly parse such frames (for details see
  Section 3.6 and 6.8 in the paper).

- `eapol-amsdu BP` and `eapol-amsdu-bad BP`: to confirm the result of this test you have to run wireshark
  or tcpdump on the victim, and monitor whether the injected ping request is received by the victim. In
  tcpdump you can use the filter `icmp` and in wireshark you can also use the filter `frame contains "test_ping_icmp"`
  to more easily detect this ping request.

## 7.8. Troubleshooting checklist

In case the test tool doesn't appear to be working, check the following:

1. Check that no other process is using the network card (e.g. kill your network manager).

2. Assure the device you are testing doesn't enter a sleep state (causing it to miss injected frames).
   I recommend running the test tool in [mixed mode](#mixed-mode) since this better handles clients
   that may go into a sleep state.

3. Run the [injection tests](#Network-card-injection-test) to make sure injection is working properly.

4. Check that you machine isn't generating background traffic that interferes with the tests. In
   particular, disable networking in your OS, manually kill your DHCP client/server, etc. See
   also [Before every usage](#before-every-usage).

5. Confirm that you are connecting to the correct network. Double-check `client.conf`.

6. Make sure the AP being tested is using (AES-)CCMP as the encryption algorithm. Other encryption
   algorithms such as TKIP or GCMP are not supported.

7. If you updated the code using git, execute `./build.sh` again (see [Prerequisites](#prerequisites)).

8. If your Wi-Fi dongle is unreliable, use it from a live CD or USB. A virtual machine can be unreliable.

9. Confirm using a second monitor interface that no other frames are sent in between fragments.
    For instance, I found that my Intel device sometimes sends Block Ack Response Action frames
    between fragments, and this interfered with the defragmentation process of the device under test.

10. Check that you are using modified drivers if needed for your wireless network card.
    If you updated your kernel, you will need to recompile and reinstall the drivers.

11. Check that you are using modified firmware if needed for your wireless network card.

# 8. Extended Vulnerability Tests

Due to implementation variations it can be difficult to confirm/exploit certain vulnerabilities, in particular
the mixed key and cache attack. Therefore, we recommend to only consider a device secure if there are explicit
checks in the code to prevent these attacks. Additionally, if time permits, we also recommend the following more
advanced tests. These have a lower chance of uncovering new vulnerabilities, but might reveal attack variants
or particular device behaviour that the normal tests can't detect.

If the normal tests in [Testing for Vulnerabilities](#Testing-for-Vulnerabilities) have already confirmed the
presence of a certain vulnerability class, there is no need to test the other attack variants of that vulnerability.

|                Command                 | Short description
| -------------------------------------- | ---------------------------------
| <div align="center">*A-MSDU attacks (§3)*</div>
| `ping I,E --amsdu-fake`                | If this test succeeds, the A-MSDU flag is ignored (§3.5).
| `ping I,E --amsdu-fake --amsdu-ssp`    | Check if the A-MSDU flag is authenticated but then ignored (§3.5).
| `amsdu-inject`                         | Send A-MSDU frame whose start is also a valid rfc1042 header (§3.2).
| `amsdu-inject-bad`                     | Same as above, but against targets that incorrectly parse the frame.
| <div align="center">*Mixed key attacks (§4)*</div>
| `ping I,E,F,AE`                        | If no (encrypted) data frames are accepted during the rekey handshake.
| `ping I,F,BE,E`                        | In case the new key is installed relatively late.
| `ping I,E,F,AE --rekey-plain`          | If the device performs the rekey handshake in plaintext.
| `ping I,E,F,AE --rekey-req --rekey-plain`| Same as above, and actively request a rekey as client.
| `ping I,E,F,AE --rekey-early-install`  | Install the new key before sending message 4 as an AP. **TODO: Test again against Windows.**
| `ping I,F,BE,AE --freebsd`             | Mixed key attack against FreeBSD.
| <div align="center">*Cache attacks (§5)*</div>
| `ping I,E,R,AE --freebsd [--full-reconnect]` | Cache attack specific to FreeBSD implementations.
| `ping I,E,R,AP --freebsd [--full-reconnect]` | Cache attack specific to FreeBSD implementations.
| <div align="center">*Mixed plain/encrypt attack (§6.3)*</div>
| `ping I,E,E --amsdu`                   | Send a normal ping as a fragmented A-MSDU frame.
| `ping I,E,P,E`                         | Ping with first frag. encrypted, second plaintext, third encrypted.
| `linux-plain 3`                        | Same as linux-plain but decoy fragment is sent using QoS priority 3.
| <div align="center">*AP forwards EAPOL attack (§6.4)*</div>
| `eapol-inject 00:11:22:33:44:55`       | Test if AP forwards EAPOL frames before authenticated (use tcpdump).
| `eapol-inject-large 00:11:22:33:44:55` | Make AP send fragmented frames by EAPOL injection (use tcpdump).
| <div align="center">*No fragmentation support attack (§6.6)*</div>
| `ping I,E,D`                           | Send ping inside an encrypted first fragment (no 2nd fragment).
| `ping I,D,E`                           | Send ping inside an encrypted second fragment (no 1st fragment).
| <div align="center">*Broadcast fragment attack (§6.7)*</div>
| `ping I,P --bcast-ra`                  | Ping in a plaintext broadcast Wi-Fi frame after 4-way HS.
| `ping BP --bcast-ra`                   | Ping in a plaintext broadcast Wi-Fi frame before 4-way HS (use tcpdump).
| `eapfrag BP,BP`                        | Specalization of broadcast fragment attack (experimental, use tcpdump).
| <div align="center">*A-MSDUs EAPOL attack (§6.8)*</div>
| `eapol-amsdu[-bad] BP --bcast-dst`     | Same as "eapol-amsdu BP" but easier to verify against APs (with tcpdump).

## 8.1. A-MSDU attack tests (§3)

It is only useful to execute the first two tests if the main test `ping I,E --amsdu` fails and you want to better
understand how the tested device handles A-MSDU frames:

- `ping I,E --amsdu-fake`: If this tests succeeds, the receiver treats all frames as normal frames (meaning it doesn't
  support A-MSDU frames). This behaviour is not ideal, although it is unlikely that an attacker can abuse this in
  practice (see Section 3.5 in the paper).

- `ping I,E --amsdu-fake --amsdu-ssp`: If this tests succeeds, the receiver authenticates the QoS A-MSDU flag of every
  received frame (i.e. it will not mask it to zero on reception) but then treats all received frames as normal frames
  (meaning it does not support the reception of real A-MSDU frames). This behaviour is not ideal, although it is unlikely
  that an attacker can abuse this in practice (see Section 3.5 in the paper).

The last two tests are used to simulate our A-MSDU injection attack:

- `amsdu-inject`: This test simulates the A-MSDU injection attack described in Section 3.2 of the paper. In particular,
  it sends an A-MSDU frame whose starts is also a valid rfc1042 header (since this is also what happens in our reference
  attack).
  
- `amsdu-inject-bad`: Some devices incorrectly parse A-MSDU frames that start with a valid rfc1042 header causing the
  above test to fail. In that case try `amsdu-inject-bad` instead (see Section 3.6 in the paper). Note that if this tests
  succeeds, the impact of the attack is effectively identical to implementations that correctly parse such frames.

## 8.2. Mixed key attack tests (§4)

Most devices we tested are vulnerable to mixed key attacks. In case the normal mixed key attack tests indicate
that a device is not vulnerable, but the test `ping-frag-sep` does succeed, it is highly recommended to try
these alternative mixed key attack tests. Some remarks:

- Home routers with a MediaTek driver will perform the rekey handshake in plaintext. To test these or similar
  devices, you must add the `--rekey-plain` parameter. When testing an AP this can be combined with the
  `--rekey-req` parameter to actively request a rekey.

- Certain clients install the key too early during a pairwise session rekey. To test these devices, add the
  `--rekey-early-install` parameter and retry the test.

Finally, in case the test `ping-frag-sep` doesn't succeed, you can try the following test:

- `ping I,F,BE,AE --freebsd`: this essentially performs the rekey handshake against a FreeBSD implementation or
  driver without affecting the defragmentation process of data frames. See Appendix F in the paper for details.

## 8.3. Cache attack tests (§5)

- The test `ping I,E,R,AE --freebsd --full-reconnect` can be used to check if a FreeBSD AP, or an implementation
  based on FreeBSD drivers, is vulnerable to a cache attack. See Appendix F in the paper for details on how this
  test works. You should also try this test without the `--full-reconnect` parameter.

- The test `ping I,E,R,AP --freebsd --full-reconnect` is a variant against FreeBSD APs, or an implementation based
  on FreeBSD drivers, where the second fragment is sent in plaintext after reconnecting with the AP. Against some
  dongles on FreeBSD this test was more reliable and still proves that old fragments remain in the AP's memory after
  reconnecting. You should also try this test without the `--full-reconnect` parameter.

## 8.4. Mixed plain/encrypt attack (§6.3)

- `ping I,E,E --amsdu`: This test sends a fragmented A-MSDU frame, which not all devices can properly receive.
  This test is useful to determine the practical exploitability of the "Mixed plain/encrypt attack".
  Summarized, if this tests succeeds, it is easier to attack the device if the second fragment can be sent
  in plaintext (test `ping I,E,P`). See Section 6.3 of the paper for details.

- `ping I,E,P,E` and `linux-plain 3`: You can try these two mixed plain/encrypt attack test if all the other ones
  in [Testing for Vulnerabilities](#Testing-for-Vulnerabilities) didn't succeed.

## 8.5. AP forwards EAPOL attack tests (§6.4)

- `eapol-inject 00:11:22:33:44:55`: This test is only meaningfull against APs. To perform this test you have to connect
  to the network using a second device and replace the MAC address `00:11:22:33:44:55` with the MAC address of this second
  device. The test will try to send an EAPOL frame to this second device (before being authenticated). If the AP forwards
  the EAPOL frame to the second device, the AP is considered vulnerable. To confirm if the AP forwards the EAPOL frame you
  must run tcpdump or wireshark on the second device. You can use the wireshark filter `frame contains "forwarded_data"`
  when monitoring decrypted traffic on the wireless interface of the second device (or the tcpdump filter `ether proto 0x888e`
  to monitor all EAPOL frames). See Section 6.4 of the paper for the details and impact if this test succeeds.

- `eapol-inject-lage 00:11:22:33:44:55`: In case the above `eapol-inject` works, you can also try `eapol-inject-large` to see
  if this vulnerability can be abused to force the transmission of encrypted fragments. You again have to use tcpdump or wireshark
  to check this. Use the wireshark or tshark filter `(wlan.fc.frag == 1) || (wlan.frag > 0)` to detect fragmented frames. It is
  rare for this attack to work.

## 8.6. Abusing no fragmentation support (§6.6)

If one of these tests works, the device doesn't support (de)fragmentation, but is still vulnerable to attacks. The
problem is that the receiver treats fragmented frames as full frames (see Section 6.6 in the paper).

## 8.7. Broadcast fragment attack tests (§6.7)

- Because all these tests send broadcast frames, which are not automatically retransmitted, it is recommended to
  execute them tests several times. This is because background noise may prevent the tested devices from receiving
  the injected broadcast frame. Additionally, we only expect that clients might be vulnerable to these attacks.

- `ping I,P --bcast-ra`: this sends a unicast ICMP ping request inside a plaintext broadcast Wi-Fi frame. This test
  only makes sense against a client.

- `ping BP --bcast-ra`: similar to the above test `ping I,P --bcast-ra`, but the ping is sent before the client has
  authenticated with the network. You must run tcpdump or wireshark to check if the client accepts the frame. In
  tcpdump you can use the filter `icmp` and in wireshark you can also use the filter `frame contains "test_ping_icmp"`
  to more easily detect this ping request.

- `eapfrag BP,BP`: this is a specialization of the above two tests that is performed before the client has authenticated.
  It is a _very experimental_ attack based on the analysis of leaked code. It first sends a plaintext fragment that starts
  with an EAPOL header, which is accepted because the 4-way handshake is still being executed. Then it sends a second
  broadcast fragment with the same sequence number. Based on the analysis of leaked code some devices may now accept
  this fragment (because the previous fragment was allowed), but the subsequent code will process it as a normal frame
  (because the fragment is broadcasted). You must use tcpdump or wireshark on the victim to determine whether the frame
  is properly received, for example using the filter `icmp` or `frame contains "test_ping_icmp"`. An alternative variant
  is `eapfrag BP,AE` in case the normal variant doesn't work.

## 8.8. A-MSDU EAPOL attack tests (§6.8)

This test can be used in case you want to execute the `eapol-amsdu[-bad] BP` tests but cannot run tcpdump or wireshark on
the AP. This means this test is only meaningfull against APs. In particular, the command `eapol-amsdu[-bad] BP --bcast-dst`
will cause a vulnerable AP to broadcast the ping request to all connected clients. In other words, to check if an AP is
vulnerable, execute this command, and listen for broadcast Wi-Fi frames on a second device that is connected to the AP by
using the filter `icmp` or `frame contains "test_ping_icmp"`.

# 9. Advanced Usage

## 9.1. Network card injection test

### Injection and hwsim mode

The script `test-injection.py` can be used to test whether frames are properly injected when
using _injection mode_:

	./test-injection.py wlan0 wlan1

Here we test if network card `wlan0` properly injects frames and we use network card `wlan1`
to monitor whether frames are properly injected. Note that both interfaces need to support
monitor mode for this test script to work.

In case you do not have a second network card, you can execute a partial injection test using:

	./test-injection.py wlan0

Unfortunately, the above test can only test if the kernel overwrites fields of injected frames,
it cannot test whether the firmware or wireless chip itself overwrites fields.

### Mixed mode

To test whether a network card properly injects frames in _mixed mode_, you can execute the
following two commands:

	./fragattack wlan0 ping --inject-test wlan1
	./fragattack wlan0 ping --inject-test wlan1 --ap

Here we test whether `wlan0` properly injects frames by monitoring the injected frames using the
second network card `wlan1`. The first command tests if frames are properly injected when using
mixed mode while acting as a client, and the second command when using mixed mode while acting
as an AP. In order to start the test, the client must be able to connect to a network, and the
AP waits until a client is connecting before starting the injection tests.

If you also want to test the retransmission behaviour of `wlan0` in mixed mode you can execute:

	./fragattack wlan0 ping --inject-test-postauth wlan1
	./fragattack wlan0 ping --inject-test-postauth wlan1 --ap

In case you do not have a second network card, you can execute a partial mixed mode injection test
using:

	./fragattack wlan0 ping --inject-selftest
	./fragattack wlan0 ping --inject-selftest --ap

Unfortunately, the above tests can only test if the kernel overwrites fields of injected frames,
it cannot test whether the firmware or wireless chip itself overwrites fields.

### Interpreting test results

First, the injection scripts only test the most important behaviour. The best way to confirm that injection
is properly working is to **perform the vulnerability tests against devices that are known to be vulnerable**,
and confirming that the tool correctly identifies the device(s) as vulnerable.

In case the injection tests are not working, try to first unplug your Wi-Fi dongles and reboot your computer.
If the tests still fail, try to use a different network card to monitor whether frames are injected properly.
I observed that sometimes frames are in fact properly injected, but the second network card (`wlan1`
in the above examples) did not recieve most injected frames. What also helps is running the tests and
experiments in an environment (and on a channel) with little background noise.

The test script will give detailed output on which tests succeeded or failed, and will conclude by outputting
either "==> The most important tests have been passed successfully" or a message indicating that either important
tests failed or that it couldn't capture certain inject frames. When certain injected frames could not be captures,
this by either be because of background noise, or because the network card being tested is unable to properly
inject certain frames (e.g. the firmware of the Intel AX200 crashes when injecting fragmented frames).

### Manual checks notes

When using wireshark to inspect the injection behaviour of a device it is recommended to use a second
device in monitor mode to see how frames are injected. In case you open the interface used to inject
frames then you should see injected frames twice: (1) first you see the frame as injected by whatever
tool is sending it, and then (2) a second time by how the frame was injected by the driver. These two
frames may slightly differ if the kernel overwrote certain fields. If you only see an injected frame once
it may have been dropped by the kernel.

## 9.2. Static IP Configuration

In case the device you are testing doesn't support DHCP, you can manually specify the IP addresses
that the test tool should use. For example:

	./fragattack.py wlan0 [--ap] ping --inject wlan1 --ip 192.168.100.10 --peerip 192.168.100.1

Here the test tool will use IP address 192.168.100.10, and it will inject a ping request to the peer
IP address 192.168.100.1.

When a test sends IP packets before obtaining IP addresses using DHCP, it will use the default IP
address 127.0.0.1. To use different (default) IP addresses, you can also use the `--ip` and `-peerip`
parameters.

## 9.3. No ICMP Support

**TODO: Alternatives --arp and --dhcp if the tested device doesn't reply to pings.**

## 9.4. Alternative network cards

In case you cannot get access to one of the recommended wireless network cards, a second option
is to get a network card that uses the same drivers on Linux. In particular, you can try:

1. Network cards that use [ath9k_htc](https://wikidevi.wi-cat.ru/Ath9k_htc)

2. Network cards that use [carl9170](https://wikidevi.wi-cat.ru/carl9170)

3. Network cards that use [iwlmvm](https://wireless.wiki.kernel.org/en/users/drivers/iwlwifi).

I recommend cards based on `ath9khtc`. Not all cards that use `iwlmvm` will be compatible. When
using an alternative network card, I strongly recommend to first run the [injection tests](#Network-card-injection-test)
to confirm that the network card is compatible.

## 9.5. 5 GHz support

In order to use the test tool on 5 GHz channels the network card being used must allow the injection
of frames in the 5 GHz channel. Unfortunately, this is not always possible due to regulatory
constraints. To see on which channels you can inject frames you can execute `iw list` and look under
Frequencies for channels that are _not_ marked as disabled, no IR, or radar detection. Note that these
conditions may depend on your network card, the current configured country, and the AP you are
connected to. For more information see, for example, the [Arch Linux documentation](https://wiki.archlinux.org/index.php/Network_configuration/Wireless#Respecting_the_regulatory_domain).

Although I have not yet encountered a device that behaved differently in the 2.4 GHz band compared
to the 5 GHz band, this may occur in practice if different drivers are used to handle both bands.
If you encounter such a case please let us know. Since I have not yet observed such differences
between the 2.4 and 5 GHz band I believe that it is sufficient to only test only one of these bands.

Note that in mixed mode the Linux kernel may not allow the injection of frames even though it is
allowed to send normal frames. This is because in `ieee80211_monitor_start_xmit` the kernel refuses
to inject frames when `cfg80211_reg_can_beacon` returns false. As a result, Linux may refuse to
inject frames even though this is actually allowed. Making `cfg80211_reg_can_beacon` return true
under the correct conditions prevents this bug.

## 9.6. Notes on device support

### ath9k_htc

The Technoethical N150 HGA, TP-Link TL-WN722N v1.x, and Alfa AWUS036NHA, all use the `ath9k_htc` driver.

For me these devices worked fairly well in a virtual machine, although like with all devices they are
more reliably when used natively. When using a VM, I recommend to configure the VM to use a USB2.0
controller, since that appeared more stable (at least with VirtualBox).

In recent kernels there was a (now fixed) regression with the `ath9k_htc` driver causing it not te work.
Simply use an up-to-date kernel to avoid this issue. The patch that fixed this regression is:
https://www.spinics.net/lists/linux-wireless/msg200825.html

### AWUS036ACM

If for some reason Linux does not automatically recognize this device, execute `sudo modprobe mt76x2u`
to manually load the driver. I found that, at least on my devices, this dongle was unstable when connected
to a USB3.0 ports. Others seems to have reported [similar issues](https://www.spinics.net/lists/linux-wireless/msg200453.html)
with this dongle. When connected to a USB2.0 port I found this dongle to be reliable.

#### AWUS036ACH

This device is generally not supported by default in most Linux distributions and requires manual
installation of drivers. I tested it on Kali Linux after installing the driver using the instructions
on [https://github.com/aircrack-ng/rtl8812au](GitHub). Before plugging in the device, you must
execute `modprobe 88XXau rtw_monitor_retransmit=1`. Once my patches have reached upstream repositories
on Kali Linux you can simply install the driver using `sudo apt install realtek-rtl88xxau-dkms`, but
for now you must manually install the driver from GitHub.

### Intel AX200

I tested the Intel AX200 as well and found that it is _not_ compatible with the test tool: its firmware
crashes after sending a fragmented frame. If an Intel developer is reading this, please update the firmware
and make it possible to inject fragmented frames.

### Injection mode

**TODO: Device that were tested as being an AP while using another one to inject? Broadcom of macOS, Intel AX200?**

## 9.7. Hwsim mode details

**Warning**: *this is currently an experimental mode, only use it for research purposes.*

This mode requires only one network card that supports monitor mode, and in contrast to mixed mode, the
network card does not have to support virtual interfaces. The disadvantage is that in this mode frames
are handled a bit slower, and it is not reliable when the network card does not acknowledge frames:

- Due to commit 1672c0e31917 ("mac80211: start auth/assoc timeout on frame status") authentication
  as a client will instantly timeout, meaning we cannot use hwsim mode as a client currently.
  _TODO: We need to patch the kernel to avoid this timeout._

- If we test a client that uses commit 1672c0e31917 ("mac80211: start auth/assoc timeout on frame status")
  we (as an AP) must acknowledge frames sent towards us. Otherwise the client being tested will be
  unable to connected.
  _TODO: Test which devices acknowledge frames in monitor mode, and test `iw set wlanX monitor active`._

- Certain APs will also require that authentication and association frames are acknowlegded by the client.
  This that that we (as a client) must again acknowledge frames sent towards us.
  _TODO: Test which devices acknowledge frames in monitor mode, and test `iw set wlanX monitor active`._

- For some strange reason, the Intel/mvm cannot receive data frames from Android/iPhone/iPad
  after 4-way HS? This is a very strange bug. _TODO: Investigate this further._

Before using this mode, create two virtual network cards:

	./hwsim.sh

This will output the two created virtual "hwsim" interfaces, for example wlan1 and wlan2. When testing
an AP in this mode, you must first search for the channel of the AP, and put the real network card on
this channel:

	./scan.sh wlan0
	ifconfig wlan0 down
	iw wlan0 set type monitor
	ifconfig wlan0 up
	# Pick the channel that the AP is on (in this example 11)
	iw wlan0 set channel 11

Here wlan0 refers to the _real_ network card (not an interface created by `hwsim.sh`). hen testing a
client, do do not first have to configure the channel (it is taken from `hostapd.conf`). You can now
start the test tool as follows:

	./fragattack wlan0 --hwsim wlan1,wlan2 [--ap] $COMMAND

After the tool executed, you can directly run it again with a new `$COMMAND`.
