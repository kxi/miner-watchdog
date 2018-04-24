import gspread
from oauth2client.service_account import ServiceAccountCredentials

def tester():

	scope = ['https://spreadsheets.google.com/feeds']
	creds = ServiceAccountCredentials.from_json_keyfile_name('key3.json', scope)
	gc = gspread.authorize(creds)
	wks = gc.open_by_url("https://docs.google.com/spreadsheets/d/12G_XdpgLKY_nb3zYI1BWfncjMJBcqVROkHoJcXO-JcE").worksheet("Coin Switch")
	coin = wks.acell('B2').value
	print(coin)
def main():
	tester()

main()
