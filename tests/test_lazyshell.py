from src.lazyshell import shell_import
import pytest


def test_simple():
    pd=shell_import('pandas')

def test_call():
    pd=shell_import('pandas')
    df=pd.dataframe()
    print(df)

def test_multi():
    pd,np,notfound=shell_import('pandas','np','doesnotexist')

    if pd:
        print('Pandas found')
        df=pd.dataframe()
        print(df)
    else:
        raise ValueError("Pandas not working")

    if notfound:
        raise ValueError("Does not exist")

def test_submodule():
    Environment=shell_import('jinja2.Environment')
    test=Environment('something')


if __name__=='main':
    pytest.main()
