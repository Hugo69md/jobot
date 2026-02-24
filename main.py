from utils.a_init.init import init
from utils.b_scraper.launcher import run_scraper

def main():
    #creation of direction folder 
    date = init()

    #run the scraper
    run_scraper(date)


if __name__ == "__main__":    
    main()
    
