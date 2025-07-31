from src.lazyshell import shell_import



def manual_tests():
    pd,np,notfound=shell_import('pandas','np','doesnotexist')

    if pd:
        print('Pandas found')
        df=pd.dataframe()
        print(df)
    else:
        raise ValueError("Pandas not working")

    if notfound:
        raise ValueError("Does not exist")


manual_tests()