#!/usr/bin/env python3
# Copyright (c) 2020, Mathy Vanhoef <mathy.vanhoef@nyu.edu>
#
# This code may be distributed under the terms of the BSD license.
# See README for more details.

# Note that tests_*.py files are imported automatically
import glob, importlib
from fraginternals import *

# ----------------------------------- Main Function -----------------------------------

def cleanup():
	daemon.stop()

def char2trigger(c):
	if c == 'S': return Action.StartAuth
	elif c == 'B': return Action.BeforeAuth
	elif c == 'A': return Action.AfterAuth
	elif c == 'C': return Action.Connected
	else: raise Exception("Unknown trigger character " + c)

def stract2action(stract):
	"""Parse a single trigger and action pair"""

	if len(stract) == 1:
		trigger = Action.Connected
		c = stract[0]
	else:
		trigger = char2trigger(stract[0])
		c = stract[1]

	if c == 'I':
		return Action(trigger, action=Action.GetIp)
	elif c == 'F':
		return Action(trigger, action=Action.Rekey)
	elif c == 'R':
		return Action(trigger, action=Action.Reconnect)
	elif c == 'P':
		return Action(trigger, enc=False)
	elif c == 'E':
		return Action(trigger, enc=True)
	elif c == 'D':
		# Note: the trigger condition of MetaDrop is ignored
		return Action(meta_action=Action.MetaDrop)

	raise Exception("Unrecognized action")

def str2actions(stractions, default):
	"""Parse a list of trigger and action pairs"""
	if stractions != None:
		return [stract2action(stract) for stract in stractions.split(",")]
	else:
		return default

def prepare_tests(opt):
	stractions = opt.actions
	if opt.testname == "ping":
		actions = str2actions(stractions,
				[Action(Action.Connected, action=Action.GetIp),
				 Action(Action.Connected, enc=True)])
		test = PingTest(REQ_ICMP, actions, opt=opt)

	elif opt.testname == "ping-frag-sep":
		# Check if we can send frames in between fragments. The seperator by default uses a different
		# QoS TID. The second fragment must use an incremental PN compared to the first fragment.
		# So this also tests if the receivers uses a per-QoS receive replay counter. By overriding
		# the TID you can check whether fragments are cached for multiple sequence numbers in one TID.
		tid = 1 if stractions == None else int(stractions)
		separator = Dot11(type="Data", subtype=8, SC=(33 << 4) | 0)/Dot11QoS(TID=tid)/LLC()/SNAP()
		test = PingTest(REQ_ICMP,
				[Action(Action.Connected, action=Action.GetIp),
				 Action(Action.Connected, enc=True),
				 Action(Action.Connected, enc=True, inc_pn=0)],
				 separate_with=separator, opt=opt)

	elif opt.testname == "wep-mixed-key":
		log(WARNING, "Cannot predict WEP key reotation. Fragment may time out, use very short key rotation!", color="orange")
		test = PingTest(REQ_ICMP,
				[Action(Action.Connected, action=Action.GetIp),
				 Action(Action.Connected, enc=True),
				 # On a WEP key rotation we get a Connected event. So wait for that.
				 Action(Action.AfterAuth, enc=True),
				])

	elif opt.testname == "cache-poison":
		# Cache poison attack. Worked against Linux Hostapd and RT-AC51U.
		test = PingTest(REQ_ICMP,
				[Action(Action.Connected, enc=True),
				 Action(Action.Connected, action=Action.Reconnect),
				 Action(Action.AfterAuth, enc=True)])

	elif opt.testname == "forward":
		test = ForwardTest(eapol=False, dst=stractions)

	elif opt.testname in ["eapol-inject", "eapol-inject-large"]:
		large = opt.testname.endswith("-large")
		test = ForwardTest(eapol=True, dst=stractions, large=large)

	elif opt.testname in ["eapol-amsdu", "eapol-amsdu-bad"]:
		freebsd = opt.testname.endswith("-bad")
		actions = str2actions(stractions,
				[Action(Action.StartAuth, enc=False),
				 Action(Action.StartAuth, enc=False)])
		test = EapolAmsduTest(REQ_ICMP, actions, freebsd, opt)

	elif opt.testname == "linux-plain":
		decoy_tid = None if stractions == None else int(stractions)
		test = LinuxTest(REQ_ICMP, decoy_tid)

	elif opt.testname == "eapfrag":
		actions = str2actions(stractions,
				[Action(Action.StartAuth, enc=False),
				 Action(Action.StartAuth, enc=False)])
		test = BcastEapFragTest(REQ_ICMP, actions, opt.bcast_dst)

	elif opt.testname == "qca-test":
		test = QcaDriverTest()

	elif opt.testname == "qca-split":
		test = QcaTestSplit()

	elif opt.testname == "qca-rekey":
		test = QcaDriverRekey()

	elif opt.testname in ["amsdu-inject", "amsdu-inject-bad"]:
		malformed = opt.testname.endswith("-bad")
		test = AmsduInject(REQ_ICMP, malformed)

	# No valid test ID/name was given
	else: return None

	# If requested, override delay and inc_pn parameters in the test.
	test.set_general_options(opt.delay, opt.inc_pn)

	# If requested, override the ptype
	if opt.ptype != None:
		if not hasattr(test, "ptype"):
			log(WARNING, "Cannot override request type of the selected test.")
			quit(1)
		test.ptype = opt.ptype

	return test

def args2ptype(args):
	# Only one of these should be given
	if args.arp + args.dhcp + args.icmp + args.ipv6 > 1:
		log(STATUS, "You cannot combine --arp, --dhcp, --ipv6, or --icmp. Please only supply one of them.")
		quit(1)

	if args.arp: return REQ_ARP
	if args.dhcp: return REQ_DHCP
	if args.icmp: return REQ_ICMP
	if args.ipv6: return REQ_ICMPv6_RA
	if args.udp: return REQ_UDP

	return None

def args2msdu(args):
	# Only one of these should be given
	if args.amsdu + args.fake_amsdu > 1:
		log(STATUS, "You cannot combine --amsdu and --fake-amsdu. Please only supply one of them.")
		quit(1)

	if args.amsdu: return 1
	if args.fake_amsdu: return 2

	return None

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Test for fragmentation vulnerabilities.")
	parser.add_argument('iface', help="Interface to use for the tests.")
	parser.add_argument('testname', help="Name or identifier of the test to run.")
	parser.add_argument('actions', nargs='?', help="Optional textual descriptions of actions")
	parser.add_argument('--inject', default=None, help="Interface to use to inject frames.")
	parser.add_argument('--inject-test', default=None, help="Use given interface to test injection through monitor interface.")
	parser.add_argument('--inject-test-postauth', default=None, help="Same as --inject-test but run the test after authenticating.")
	parser.add_argument('--hwsim', default=None, help="Use provided interface in monitor mode, and simulate AP/client through hwsim.")
	parser.add_argument('--ip', help="IP we as a sender should use.")
	parser.add_argument('--peerip', help="IP of the device we will test.")
	parser.add_argument('--ap', default=False, action='store_true', help="Act as an AP to test clients.")
	parser.add_argument('--debug', type=int, default=0, help="Debug output level.")
	parser.add_argument('--delay', type=float, default=0, help="Delay between fragments in certain tests.")
	parser.add_argument('--inc-pn', type=int, help="To test non-sequential packet number in fragments.")
	parser.add_argument('--amsdu', default=False, action='store_true', help="Encapsulate pings in an A-MSDU frame.")
	parser.add_argument('--fake-amsdu', default=False, action='store_true', help="Set A-MSDU flag but include normal payload.")
	parser.add_argument('--arp', default=False, action='store_true', help="Override default request with ARP request.")
	parser.add_argument('--dhcp', default=False, action='store_true', help="Override default request with DHCP discover.")
	parser.add_argument('--icmp', default=False, action='store_true', help="Override default request with ICMP ping request.")
	parser.add_argument('--ipv6', default=False, action='store_true', help="Override default request with ICMPv6 router advertisement.")
	# TODO: Test the --udp option more
	parser.add_argument('--udp', type=int, default=None, help="Override default request with UDP packet to the given port.")
	parser.add_argument('--no-dhcp', default=False, action='store_true', help="Do not reply to DHCP requests as an AP.")
	parser.add_argument('--icmp-size', type=int, default=None, help="Second to wait after AfterAuth before triggering Connected event")
	parser.add_argument('--padding', type=int, default=None, help="Add padding data to ARP/DHCP/ICMP requests.")
	parser.add_argument('--rekey-request', default=False, action='store_true', help="Actively request PTK rekey as client.")
	parser.add_argument('--rekey-plaintext', default=False, action='store_true', help="Do PTK rekey with plaintext EAPOL frames.")
	parser.add_argument('--rekey-early-install', default=False, action='store_true', help="Install PTK after sending Msg3 during rekey.")
	parser.add_argument('--full-reconnect', default=False, action='store_true', help="Reconnect by deauthenticating first.")
	parser.add_argument('--bcast-ra', default=False, action='store_true', help="Send pings using broadcast *receiver* address (= addr1).")
	parser.add_argument('--bcast-dst', default=False, action='store_true', help="Send pings using broadcast *destination* when to AP ().")
	# TODO: Properly test the --bad-mic option
	parser.add_argument('--bad-mic', default=False, action='store_true', help="Send pings using an invalid authentication tag.")
	parser.add_argument('--pn-per-qos', default=False, action='store_true', help="Use separate Tx packet counter for each QoS TID.")
	parser.add_argument('--freebsd-cache', default=False, action='store_true', help="Sent EAP(OL) frames as (malformed) broadcast EAPOL/A-MSDUs.")
	parser.add_argument('--connected-delay', type=float, default=1, help="Second to wait after AfterAuth before triggering Connected event")
	parser.add_argument('--to-self', default=False, action='store_true', help="Send ARP/DHCP/ICMP with same src and dst MAC address.")
	parser.add_argument('--no-drivercheck', default=False, action='store_true', help="Don't check if patched drivers are being used.")
	options = parser.parse_args()

	# Default value for options that should not be command line parameters
	options.inject_mf_workaround = False

	# Sanity check and convert some arguments to more usable form
	options.ptype = args2ptype(options)
	options.as_msdu = args2msdu(options)

	# Make the --inject-test-postauth flags easier to check
	if options.inject_test_postauth != None:
		options.inject_test = options.inject_test_postauth
		options.inject_test_postauth = True

	else:
		options.inject_test_postauth = False

	# Dynamically import tests depending on their availability in the directory
	for test in glob("tests_*.py"):
		module = importlib.import_module(test[:-3])
		globals().update(
			{n: getattr(module, n) for n in module.__all__} if hasattr(module, '__all__') 
			else
			{k: v for (k, v) in module.__dict__.items() if not k.startswith('_')
		})

	# Construct the test
	options.test = prepare_tests(options)
	if options.test == None:
		log(STATUS, f"Test name/id '{options.testname}' not recognized. Specify a valid test case.")
		quit(1)

	# Parse remaining options
	change_log_level(-options.debug)

	# Now start the tests --- TODO: Inject Deauths before connecting with client...
	if options.ap:
		daemon = Authenticator(options)
	else:
		daemon = Supplicant(options)
	atexit.register(cleanup)
	daemon.run()
