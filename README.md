# SensorDataExtractor
A simple GUI to extract data at given timestamps from multi-sensor data (Temperature, pH, Conductivity, Current, Light)

![Interface](https://github.com/fritzfrancisco/SensorDataExtractor/blob/main/gui.jpg)

## Installation

1. Install [Miniconda](https://docs.anaconda.com/miniconda/)  

2. Create [conda](https://docs.anaconda.com/miniconda/) environment  
```conda create -f environment.yaml```

3. On MacOS or Linux in a terminal run:  
```cd /path/to/SensorDataExtractor/directory```  
```chmod +x SensorDataExtractor.py```

4. To start the GUI:  
```conda activate behavior```  
```./SensorDataExtractor.py```

5. **[Optional]** Install [pyinstaller](https://pyinstaller.org/en/stable/) to create a standalone executable file  
```pip install pyinstaller```  
```pyinstaller SensorDataExtractor.py --hidden-import openpyxl.cell._writer```  
This will create a ```dist``` folder in the current directory in which there should be an executable file.  
This allows the program to be started with a double-click.  
