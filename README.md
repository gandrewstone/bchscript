# BCHScript Compiler
Bitcoin Cash Script Language Compiler


## Running the BCHScript Compiler

```
usage: bchc [-h] [--hex] [--opc] [--verbose] [-o OUTPUT] [input]

positional arguments:
  input       input file or string program

optional arguments:
  -h, --help  show this help message and exit
  --hex       compile into hex
  --opc       compile into opcodes
  --verbose   dump everything
  -o OUTPUT   write output to specified file
```

### Examples

The following examples uses the simple.bch program located in "examples".  This program is as follows:

```
def p2pkh(pubkeyhash, @sig, @pubkey)
  {
  @sig
  @pubkey
  OP_DUP
  OP_HASH160
  pubkeyhash
  OP_EQUALVERIFY
  OP_CHECKSIG
  }

scriptify!("main", p2pkh(bchtest:qpcg8q5kp90fq9nh6acjxwvk9lnaj7puzcmel2cx5c))
scriptify!("anotherScript", p2pkh(bchreg:qpsh6hn4kapn2l9s20dgf87k55gll20yrc3u36taw5))
```

In this program there are 2 scripts defined, "main" (the default) and "anotherScript".


#### Compile "main" to opcodes

```
$ ./bchc --opc examples/simple.bch 
OP_DUP
OP_HASH160
bchtest:qpcg8q5kp90fq9nh6acjxwvk9lnaj7puzcmel2cx5c
OP_EQUALVERIFY
OP_CHECKSIG
```

#### Compile "main" to hex

```
$ ./bchc --hex examples/simple.bch 
76a91470838296095e901677d7712339962fe7d9783c1688ac
```

#### Compile "anotherAddr" to hex

```
$ ./bchc --hex --display anotherScript examples/simple.bch 
76a91470838296095e901677d7712339962fe7d9783c1688ac
```

#### Compile every target (to a JSON representation)

```
$ ./bchc --hex --opc --display all examples/simple.bch
{'anotherScript':  {
    'spend': ['@sig', '@pubkey'],
    'script': ['76a914617d5e75b743357cb053da849fd6a511ffa9e41e88ac', 'OP_DUP\nOP_HASH160\nbchreg:qpsh6hn4kapn2l9s20dgf87k55gll20yrc3u36taw5\nOP_EQUALVERIFY\nOP_CHECKSIGVERIFY']},
 'main': {
     'spend': ['@sig', '@pubkey'],
     'script': ['76a91470838296095e901677d7712339962fe7d9783c1688ac', 'OP_DUP\nOP_HASH160\nbchtest:qpcg8q5kp90fq9nh6acjxwvk9lnaj7puzcmel2cx5c\nOP_EQUALVERIFY\nOP_CHECKSIGVERIFY']}
}
```

#### Compile stdin to hex written to out.txt

```
$ echo "def nop2() { OP_NOP OP_NOP } scriptify!(\"main\", nop2())" | ./bchc -opc -o out.hex
stone@xanadu:/fast/bitcoin/bchscript$ cat out.hex
6161
```

## Use as a Python Library

To be written, look at the bchc program for now.

## BCHScript Language

To be written, use the examples to get the hang of it for now.

