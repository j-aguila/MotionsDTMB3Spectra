# MotionsDTMB3Spectra
- These are Motions for a DTMB battleship in 50 different realizations of 3 different sea states (total of 150 seeds) of the Pierson Moskowitz Spectrum:
       {Significant Wave Height, Spectral Peak Period, Sampling Time step}
        Sea state 1: 3.53m, 9.7s, 0.008s
        Sea state 2: 5.09m, 12.4s, 0.01s
        Sea state 3: 10.66m, 13.4s, 0.011s
- Vessel Velocity is kept constant at 30kn and it is travelling in an oblique direction to the unidirectional wave patern. The direction of the waves is 30 degrees with respect to the symetry plane of the battleship.
# Naming Convention for the Files
  - Motion Files will be permutations of the following combinations:
        {H,P,R}__{97,124,134}__{1 to 50}
        For example H_134_3.csv is the Heave motion derived from the 3rd seed of state 3 (T_p=13.4s).
  - Wave prove files will be permutations of the following combinations:
        WaveProve{X,Y}___{97,124,134}___{1 to 50}__{Ylocations or Xlocations}
        Ylocations=[250,200,150,100,50,0]
        Xlocations=[-250,-200,-150,-100,-50,0]
