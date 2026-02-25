from utils.a_init.init import init
from utils.b_scraper.launcher import run_scraper
from utils.c_ia.ia_launcher import run_ia
from utils.d_files_gen.files_gen_launcher import run_pdf_generation
def main():
    #creation of direction folder 
    date = init()

    #run the scraper
    run_scraper(date)

    #run qwen
    run_ia(date)

    #run pdf gen
    run_pdf_generation(date)

if __name__ == "__main__":    
    main()
    
