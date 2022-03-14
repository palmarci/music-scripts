import time
import aubio
import numpy as np
import sounddevice as sd
from stupidArtnet import StupidArtnet
import time

artnet = None			
# ip, universe, packet size (512), framerate(30hz), isbroadcast, ???
artnet = StupidArtnet("127.0.0.1", 0, 512, 30, True, True)
artnet.start()

sampleR = 44100
buf_size = 1024
hop_size = 512

# methods: default|energy|hfc|complex|phase|specdiff|kl|mkl|specflux
a_tempo = aubio.tempo(method="specflux", samplerate=sampleR, buf_size=buf_size, hop_size=hop_size)

stream = sd.InputStream(samplerate=sampleR, channels=1, dtype=np.float32, latency='low')
stream.start()

val = 0

while True:

	samples, overflowed = stream.read(hop_size)
	samples = samples.squeeze()


	beat = a_tempo(samples)

	if beat:
		val = not val
		print(f"sending {val}")
		artnet.set_single_value(1, val)
		artnet.show()
		time.sleep(0.5)
		#print("beat")



artnet.stop()
stream.end()
