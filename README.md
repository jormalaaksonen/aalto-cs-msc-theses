# Aalto-CS-MSc-Theses

Listing of MSc and BSc theses of the Department of Computer Science at Aalto University 

## Invocation

To see the number of MSc theses supervised by each faculty member in 2021-2024:
```
./msc-theses.py
```

Because the data collection stage is **very very** slow, it is advisable to reuse the
cached information in further invocations with the `--fast` switch:
```
./msc-theses.py --fast
```

To see additionally the schools, authors, titles and issue dates of the theses, add `--details`:
```
./msc-theses.py --fast --detail
```

To see even more the PDF availability, keywords and abstracts, add `--keywords`:
```
./msc-theses.py --fast --detail --keywords
```

To limit the output to only specific years, add `--years` and a comma-separated list:
```
./msc-theses.py --fast --years 2023,2024
```

To see all metadata related to a specific student's thesis, add `--student` and name:
```
./msc-theses.py --fast --student "John Doe"
```

To see BSc theses per advisor instead of MSC theses per supervisor, add the `--bsc` switch:
```
./msc-theses.py --bsc
./msc-theses.py --bsc --fast --detail
```

Additional switches and help:

```
./msc-theses.py --help
```

## Feedback

Any bug reports and feature requests to <<jorma.laaksonen@aalto.fi>>
