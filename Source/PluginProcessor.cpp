#include "PluginProcessor.h"
#include "PluginEditor.h"

static juce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout()
{
    std::vector<std::unique_ptr<juce::RangedAudioParameter>> params;
    params.push_back(std::make_unique<juce::AudioParameterFloat>(
        "delayTime", "Delay Time", juce::NormalisableRange<float>(1.0f, 1000.0f, 0.01f), 400.0f));
    params.push_back(std::make_unique<juce::AudioParameterFloat>(
        "wetDry", "Wet/Dry", juce::NormalisableRange<float>(0.0f, 1.0f, 0.001f), 0.5f));
    return { params.begin(), params.end() };
}

VstAiDemoAudioProcessor::VstAiDemoAudioProcessor()
    : AudioProcessor(BusesProperties()
          .withInput("Input", juce::AudioChannelSet::stereo(), true)
          .withOutput("Output", juce::AudioChannelSet::stereo(), true)),
      parameters(*this, nullptr, juce::Identifier("VstAiDemoParams"), createParameterLayout())
{
}

void VstAiDemoAudioProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
    currentSampleRate = sampleRate;
    updateDelayBufferSize();
    delayBuffer.clear();
    delayBufferWritePos = 0;
}

void VstAiDemoAudioProcessor::releaseResources()
{
    delayBuffer.setSize(1, 1, false, false, true);
}

bool VstAiDemoAudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    const auto input = layouts.getMainInputChannelSet();
    const auto output = layouts.getMainOutputChannelSet();
    return input == output &&
           (output == juce::AudioChannelSet::mono() ||
            output == juce::AudioChannelSet::stereo());
}

void VstAiDemoAudioProcessor::updateDelayBufferSize()
{
    // Max delay time: 1000 ms
    int maxDelaySamples = (int)(currentSampleRate * 1.0) + 1;
    delayBuffer.setSize(1, maxDelaySamples);
    delayBuffer.clear();
    delayBufferWritePos = 0;
}

void VstAiDemoAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer,
                                            juce::MidiBuffer& midiMessages)
{
    juce::ScopedNoDenormals noDenormals;
    juce::ignoreUnused(midiMessages);

    const int numSamples = buffer.getNumSamples();
    const int numChannels = buffer.getNumChannels();
    if (numChannels == 0) return;

    // Get parameter values
    float delayMs = parameters.getRawParameterValue("delayTime")->load();
    float wetDry = parameters.getRawParameterValue("wetDry")->load();
    float dry = 1.0f - wetDry;

    // Convert to mono (sum L+R if stereo)
    juce::AudioBuffer<float> monoBuffer(1, numSamples);
    monoBuffer.clear();
    if (numChannels == 1)
        monoBuffer.copyFrom(0, 0, buffer, 0, 0, numSamples);
    else
        for (int i = 0; i < numSamples; ++i)
            monoBuffer.setSample(0, i, 0.5f * (buffer.getSample(0, i) + buffer.getSample(1, i)));

    // Prepare delay buffer
    int delayBufferSamples = delayBuffer.getNumSamples();
    float* delayData = delayBuffer.getWritePointer(0);
    float* monoData = monoBuffer.getWritePointer(0);

    int delaySamples = juce::jlimit(1, delayBufferSamples - 1, (int)(delayMs * 0.001 * currentSampleRate));

    for (int i = 0; i < numSamples; ++i)
    {
        int readPos = delayBufferWritePos - delaySamples;
        if (readPos < 0)
            readPos += delayBufferSamples;
        float delayedSample = delayData[readPos];

        // Write current input sample to delay buffer
        delayData[delayBufferWritePos] = monoData[i];

        // Output: dry/wet mix
        float outSample = dry * monoData[i] + wetDry * delayedSample;

        // Write to all output channels (mono out)
        for (int ch = 0; ch < numChannels; ++ch)
            buffer.setSample(ch, i, outSample);

        // Increment write position
        if (++delayBufferWritePos >= delayBufferSamples)
            delayBufferWritePos = 0;
    }
}

juce::AudioProcessorEditor* VstAiDemoAudioProcessor::createEditor()
{
    return new VstAiDemoAudioProcessorEditor(*this);
}

void VstAiDemoAudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    std::unique_ptr<juce::XmlElement> xml(parameters.state.createXml());
    copyXmlToBinary(*xml, destData);
}

void VstAiDemoAudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    std::unique_ptr<juce::XmlElement> xmlState(getXmlFromBinary(data, sizeInBytes));
    if (xmlState && xmlState->hasTagName(parameters.state.getType()))
        parameters.replaceState(juce::ValueTree::fromXml(*xmlState));
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new VstAiDemoAudioProcessor();
}
