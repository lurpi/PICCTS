import sys
import mph

'''
This script will set comsol accordingly to the PICCTS coupling requirements
Initial comsol file must only contain the geometry (no study, no data, etc., see javaformatting.mph)
'''


geometry = 2 # 1 for 1D, 2 for 2D etc
interface = "tds" # tds or npe
interfaceLong = {'tds': 'DilutedSpecies',
                 # 'tdsPorous': 'DilutedSpeciesInPorousMedia',
                 'npe': 'NernstPlanck'}

systemSpeciation = ['species+1','species-2','phase'] # put your speciation here
fixedSpecies = ['phase'] # put all species here

Comsolpath = "comsolProcessing.mph" # put your Comsol path here

def ComsolFormalism(liste_entree):
    liste_sortie = []
    for nom in liste_entree:
        if nom.startswith("("):
            nom = "j" + nom
        
        nom = nom.replace("(", "_").replace(")", "_").replace(",", "_").replace(":", "_").replace('.','_')
        nom = nom.replace("-7", "minusseven")
        nom = nom.replace("-6", "minussix")
        nom = nom.replace("-5", "minusfive")
        nom = nom.replace("-4", "minusf")
        nom = nom.replace("-3", "minust")
        nom = nom.replace("-2", "minust")
        nom = nom.replace("-", "minus")
        
        nom = nom.replace("+7", "plusseven")
        nom = nom.replace("+6", "plussix")
        nom = nom.replace("+5", "plusfive")
        nom = nom.replace("+4", "plusf")
        nom = nom.replace("+3", "plust")
        nom = nom.replace("+2", "plust")
        nom = nom.replace("+", "plus")
        liste_sortie.append(nom)
    return liste_sortie



totalspc = ComsolFormalism(systemSpeciation)
spcTransported = ComsolFormalism([spc for spc in systemSpeciation if spc not in fixedSpecies])
spcFixed = ComsolFormalism(fixedSpecies)

separateur = "\t"
ligne_header =  separateur.join(['x', 'y', 'z'][:geometry] + totalspc)
ligne_valeurs = separateur.join(["0"] * len(totalspc+['x','y','z'][:geometry]) )

with open("int.txt", "w") as f:
    f.write("%" + ligne_header + "\n")
    f.write(ligne_valeurs + "\n")

client = mph.start()

model = client.load(Comsolpath)
javamodel = model.java

javamodel.component("comp1").physics().create(interface, interfaceLong[interface], "geom1");
javamodel.component("comp1").physics(interface).selection().all(); # select all domains

### setting interface ..
for i, spc in enumerate(spcTransported, start = 1):
    if interface == 'tds':
        javamodel.component("comp1").physics(interface).field("concentration").component(i, spc) # start at 1
        javamodel.component("comp1").physics(interface).feature("init1").setIndex("initc", f"{spc}i", i-1) # start at 0
        if interface == 'tdsPorous':
            javamodel.component("comp1").physics(interface).feature("porous1").feature("fluid1").set(f"DF_{spc}", ["1e-9[m^2/s]", "0", "0", "0", "1e-9[m^2/s]", "0", "0", "0", "1e-9[m^2/s]"])
        else:
            javamodel.component("comp1").physics(interface).feature("cdm1").set(f"D_{spc}", ["1e-9[m^2/s]", "0", "0", "0", "1e-9[m^2/s]", "0", "0", "0", "1e-9[m^2/s]"])
    elif interface == "npe":
        javamodel.component("comp1").physics(interface).field("concentration").component(i, spc); # start at 1
        javamodel.component("comp1").physics(interface).prop("SpeciesProperties").set("FromElectroneutrality", "2")
        javamodel.component("comp1").physics(interface).feature("sp1").setIndex("z", "1", i-1) # charge, start at 0

### input and output
javamodel.component("comp1").func().create("int1", "Interpolation");
javamodel.component("comp1").func("int1").set("source", "file");
javamodel.component("comp1").func("int1").set("filename", "int.txt");
javamodel.component("comp1").func("int1").set("defvars", "on") # spatial coord as arguments

javamodel.study().create("std1");
javamodel.study("std1").create("time", "Transient");
javamodel.study("std1").setGenPlots(False);
javamodel.study("std1").feature("time").set("tunit", "fs");

for i in range(geometry):
    javamodel.component("comp1").func("int1").setEntry("columnType", f"col{i+1}", "arg")
    javamodel.component("comp1").func("int1").setIndex("argunit", "m", i)

for i,spc in enumerate(totalspc, start = geometry+1):
    javamodel.component("comp1").func("int1").setEntry("columnType", f"col{i}", "value");
    javamodel.component("comp1").func("int1").setIndex("fununit", "mol/L", i-geometry-1)
    javamodel.component("comp1").func("int1").setEntry("funcnames", f"col{i}", f"{spc}i")

model.solve()
javamodel.result().export().create("data1", "Data")
javamodel.result().export("data1").setIndex("looplevelinput", "last", 0);
javamodel.result().export("data1").set("data", "dset1")

for i,spc in enumerate(totalspc, start = geometry+1):
    if spc in spcFixed: javamodel.result().export("data1").setIndex("expr", spc+"i", i-geometry-1);
    else: javamodel.result().export("data1").setIndex("expr", spc, i-geometry-1);
    javamodel.result().export("data1").setIndex("unit", "mol/L", i-geometry-1);
    javamodel.result().export("data1").setIndex("descr", systemSpeciation[i-geometry-1], i-geometry-1);

print('Done')
model.save()
