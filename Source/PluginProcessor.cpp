#include "PluginProcessor.h"
#include "PluginEditor.h"

VstAiDemoAudioProcessor::VstAiDemoAudioProcessor()
    : AudioProcessor(BusesProperties()
          .withInput("Input", juce::AudioChannelSet::mono(), true)
          .withOutput("Output", juce::AudioChannelSet::mono(), true)),
      apvts(*this, nullptr, juce::Identifier("Parameters"), createParameterLayout())
{
}

juce::AudioProcessorValueTreeState::ParameterLayout VstAiDemoAudioProcessor::createParameterLayout()
{
    std::vector<std::unique_ptr<juce::RangedAudioParameter>> params;
    params.push_back(std::make_unique<juce::AudioParameterFloat>(
        "delayTime", "Delay Time",
        juce::NormalisableRange<float>(0.0f, 1000.0f, 1.0f), 500.0f));
    return { params.begin(), params.end() };
}

void VstAiDemoAudioProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
    currentSampleRate = sampleRate > 0.0 ? sampleRate : 44100.0;
    delayBufferSize = static_cast<int>(currentSampleRate * 1.1); // 1.1s safety margin
    delayBuffer.clear();
    delayBuffer.resize(delayBufferSize, 0.0f);
    writePosition = 0;
}

void VstAiDemoAudioProcessor::releaseResources()
{
    delayBuffer.clear();
}

bool VstAiDemoAudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    // Only mono in/out supported
    return layouts.getMainInputChannelSet() == juce::AudioChannelSet::mono()
        && layouts.getMainOutputChannelSet() == juce::AudioChannelSet::mono();
}

void VstAiDemoAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer,
                                           juce::MidiBuffer& midiMessages)
{
    juce::ScopedNoDenormals noDenormals;
    juce::ignoreUnused(midiMessages);

    const int numSamples = buffer.getNumSamples();
    auto* channelData = buffer.getWritePointer(0);

    float delayTimeMs = apvts.getRawParameterValue("delayTime")->load();
    float delayTimeSamples = juce::jlimit(0.0f, 1000.0f, delayTimeMs) * (float)currentSampleRate / 1000.0f;

    if (delayBufferSize < (int)currentSampleRate)
        return; // Not initialized

    for (int i = 0; i < numSamples; ++i)
    {
        int readPosition = writePosition - static_cast<int>(delayTimeSamples);
        if (readPosition < 0)
            readPosition += delayBufferSize;

        float delayedSample = delayBuffer[readPosition];
        float inputSample = channelData[i];
        channelData[i] = delayedSample;
        delayBuffer[writePosition] = inputSample;

        writePosition = (writePosition + 1) % delayBufferSize;
    }
}

juce::AudioProcessorEditor* VstAiDemoAudioProcessor::createEditor()
{
    return new VstAiDemoAudioProcessorEditor(*this);
}

void VstAiDemoAudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    if (auto state = apvts.copyState())
    {
        std::unique_ptr<juce::XmlElement> xml(state.createXml());
        copyXmlToBinary(*xml, destData);
    }
}

void VstAiDemoAudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    std::unique_ptr<juce::XmlElement> xmlState(getXmlFromBinary(data, sizeInBytes));
    if (xmlState && xmlState->hasTagName(apvts.state.getType()))
        apvts.replaceState(juce::ValueTree::fromXml(*xmlState));
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new VstAiDemoAudioProcessor();
}
