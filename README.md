# Aalto-CS-MSc-Theses

Listing of M.Sc. Theses of the Department of Computer Science at Aalto University 

## Invocation

To see the number of M.Sc. Theses supervised by each faculty member in 2021-2024:
```
./msc-theses.py
```

To see additionally the schools, authors, titles and issue dates of the theses:
```
./msc-theses.py --detail
```

Because the data collection stage is rather slow, it is advisable to dump the
thesis insormation and reuse the dump in further invocations:

```
./msc-theses.py --theses=dump
```
```
./msc-theses.py --theses=load --detail
```

## Feedback

Any bug reports and feature requests to <<jorma.laaksonen@aalto.fi>>
