from site_parsers.sol.sol_monitoring import check_sol_updates
from site_parsers.sfsb.sf_sb_monitoring import check_sf_sb_updates
from datetime import datetime
import schedule


def main() -> None:
    print(datetime.now().strftime("%H:%M"))
    print('Проверяем storiesonline')
    check_sol_updates()
    print('Проверяем sf_sb')
    check_sf_sb_updates()
    print('Конец цикла')


if __name__ == '__main__':
    main()
    schedule.every().hour.do(main)
    while True:
        schedule.run_pending()
