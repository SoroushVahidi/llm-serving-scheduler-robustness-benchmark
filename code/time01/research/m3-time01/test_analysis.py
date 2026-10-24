from analyze_results import advantage,reversal,ranking

def test_exact_margin_and_direction():
    assert reversal(2.,1.,1.,2.,1) is True
    assert reversal(2.,1.,1.,2.,-1) is True
    assert reversal(1.,1.,1.,2.,1) is False
    assert reversal(0.,1.,2.,1.,1) is None
    assert reversal(None,1.,2.,1.,1) is None
    # 11/10 in binary is strictly above 1.1; use exact integer endpoint ratios
    # to check the declared strict rational boundary without rounded percentages.
    assert reversal(11.,10.,10.,11.,1) is False
    assert reversal(12.,10.,10.,12.,1) is True

def test_ties_and_missing_ranks():
    assert ranking({'a':3.,'b':3.,'c':1.,'d':0.},1)==dict(a=1.5,b=1.5,c=3.,d=4.)
    assert ranking({'a':3.,'b':3.,'c':1.,'d':0.},-1)==dict(a=3.5,b=3.5,c=2.,d=1.)
    assert ranking({'a':None,'b':1.},1) is None
